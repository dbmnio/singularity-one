#include "MCPServerRunnable.h"
#include "UnrealMCPBridge.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "JsonObjectConverter.h"
#include "Misc/ScopeLock.h"
#include "HAL/PlatformTime.h"

// Buffer size for receiving data
const int32 BufferSize = 8192;

FMCPServerRunnable::FMCPServerRunnable(UUnrealMCPBridge* InBridge, TSharedPtr<FSocket> InListenerSocket)
    : Bridge(InBridge)
    , ListenerSocket(InListenerSocket)
    , bRunning(true)
{
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Created server runnable"));
}

FMCPServerRunnable::~FMCPServerRunnable()
{
    // Note: We don't delete the sockets here as they're owned by the bridge
}

bool FMCPServerRunnable::Init()
{
    return true;
}

uint32 FMCPServerRunnable::Run()
{
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Server thread starting..."));
    
    while (bRunning)
    {
        bool bPending = false;
        if (ListenerSocket->HasPendingConnection(bPending) && bPending)
        {
            UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Client connection pending, accepting..."));
            
            FSocket* AcceptedSocket = ListenerSocket->Accept(TEXT("MCPClient"));
            if (AcceptedSocket)
            {
                // Wrap in a TSharedPtr for automatic memory management
                TSharedPtr<FSocket> NewClientSocket = MakeShareable(AcceptedSocket);

                UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Client connection accepted"));
                
                // Set socket to blocking mode for reliable communication
                NewClientSocket->SetNonBlocking(false);
                
                // Set socket options to improve connection stability
                NewClientSocket->SetNoDelay(true);
                int32 SocketBufferSize = 65536;
                NewClientSocket->SetSendBufferSize(SocketBufferSize, SocketBufferSize);
                NewClientSocket->SetReceiveBufferSize(SocketBufferSize, SocketBufferSize);

                // Handle the client connection in a loop
                HandleClientConnection(NewClientSocket);
                
                // Connection handled, close it
                NewClientSocket->Close();
                UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Client socket closed. Waiting for next connection."));
            }
            else
            {
                UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to accept client connection"));
            }
        }
        
        // Small sleep to prevent tight loop when no connections are pending
        FPlatformProcess::Sleep(0.1f);
    }
    
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Server thread stopping"));
    return 0;
}

void FMCPServerRunnable::Stop()
{
    bRunning = false;
    if (ListenerSocket)
    {
        ListenerSocket->Close();
    }
}

void FMCPServerRunnable::Exit()
{
    // Clean up any resources if needed
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Exit called"));
}

void FMCPServerRunnable::HandleClientConnection(TSharedPtr<FSocket> InClientSocket)
{
    if (!InClientSocket.IsValid() || InClientSocket->GetConnectionState() != ESocketConnectionState::SCS_Connected)
    {
        UE_LOG(LogTemp, Error, TEXT("MCPServerRunnable: Invalid or disconnected socket passed to HandleClient"));
        return;
    }

    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Starting to handle client connection"));

    // First, read the 4-byte message length (little-endian)
    uint8 LengthBytes[4];
    int32 BytesRead = 0;
    if (InClientSocket->Recv(LengthBytes, sizeof(LengthBytes), BytesRead, ESocketReceiveFlags::WaitAll))
    {
        if (BytesRead == sizeof(LengthBytes))
        {
            // Convert from little-endian bytes to uint32
            uint32 MessageLength = LengthBytes[0] | (LengthBytes[1] << 8) | (LengthBytes[2] << 16) | (LengthBytes[3] << 24);
            
            UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Received message length: %d"), MessageLength);
            
            // Validate message length to prevent buffer overflow
            if (MessageLength > 0 && MessageLength <= 65536) // Max 64KB message
            {
                // Now read the full message based on the length
                TArray<uint8> MessagePayload;
                MessagePayload.SetNumUninitialized(MessageLength);

                if (InClientSocket->Recv(MessagePayload.GetData(), MessageLength, BytesRead, ESocketReceiveFlags::WaitAll))
                {
                    if (BytesRead == MessageLength)
                    {
                        // Convert received data to string and process it
                        FString ReceivedText = FString(UTF8_TO_TCHAR(MessagePayload.GetData()));
                        
                        // Debug: Log the raw bytes to see if there are any issues
                        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Raw message bytes (first 20):"));
                        for (int32 i = 0; i < FMath::Min(20, (int32)MessagePayload.Num()); ++i)
                        {
                            UE_LOG(LogTemp, Display, TEXT("  [%d]: 0x%02X ('%c')"), i, MessagePayload[i], 
                                   (MessagePayload[i] >= 32 && MessagePayload[i] <= 126) ? (TCHAR)MessagePayload[i] : TEXT('?'));
                        }
                        
                        ProcessMessage(InClientSocket, ReceivedText);
                    }
                    else
                    {
                        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Incomplete message received. Expected %d bytes, got %d"), MessageLength, BytesRead);
                    }
                }
                else
                {
                    UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to read message payload."));
                }
            }
            else
            {
                UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Invalid message length: %d"), MessageLength);
            }
        }
        else
        {
            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to read full message length. Expected %d bytes, got %d"), sizeof(LengthBytes), BytesRead);
        }
    }
    else
    {
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to read message length header."));
    }
}

void FMCPServerRunnable::ProcessMessage(TSharedPtr<FSocket> Client, const FString& Message)
{
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Received: %s"), *Message);

    // Clean the message by removing any trailing non-printable characters
    FString CleanMessage = Message;
    CleanMessage.TrimStartAndEnd();
    
    // Debug: Log the length and last few characters
    UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Message length: %d"), CleanMessage.Len());
    if (CleanMessage.Len() > 10)
    {
        FString LastChars = CleanMessage.Right(10);
        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Last 10 characters: %s"), *LastChars);
    }
    
    // Find the last valid JSON closing brace and truncate there
    int32 LastValidBrace = -1;
    for (int32 i = CleanMessage.Len() - 1; i >= 0; --i)
    {
        TCHAR Char = CleanMessage[i];
        if (Char == TEXT('}'))
        {
            // Check if this is a valid closing brace by counting braces
            int32 BraceCount = 0;
            bool bValidBrace = true;
            for (int32 j = 0; j <= i; ++j)
            {
                TCHAR CheckChar = CleanMessage[j];
                if (CheckChar == TEXT('{'))
                {
                    BraceCount++;
                }
                else if (CheckChar == TEXT('}'))
                {
                    BraceCount--;
                    if (BraceCount < 0)
                    {
                        bValidBrace = false;
                        break;
                    }
                }
            }
            if (bValidBrace && BraceCount == 0)
            {
                LastValidBrace = i;
                break;
            }
        }
    }
    
    if (LastValidBrace >= 0)
    {
        CleanMessage = CleanMessage.Left(LastValidBrace + 1);
        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Cleaned message to: %s"), *CleanMessage);
    }
    else
    {
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Could not find valid JSON structure, using original message"));
    }

    TSharedPtr<FJsonObject> JsonObject;
    
    // Try different JSON reader approaches
    bool bParseSuccess = false;
    
    // First attempt: Standard JSON reader
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(CleanMessage);
    bParseSuccess = FJsonSerializer::Deserialize(Reader, JsonObject);
    
    // If that fails, try with a different reader type
    if (!bParseSuccess || !JsonObject.IsValid())
    {
        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: First JSON parse attempt failed, trying alternative approach"));
        
        // Try with a different reader type
        TSharedRef<TJsonReader<TCHAR>> AltReader = TJsonReaderFactory<TCHAR>::Create(CleanMessage);
        bParseSuccess = FJsonSerializer::Deserialize(AltReader, JsonObject);
    }
    
    if (!bParseSuccess || !JsonObject.IsValid())
    {
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to parse JSON from: %s"), *CleanMessage);
        return;
    }

    FString CommandType;
    if (JsonObject->TryGetStringField(TEXT("type"), CommandType))
    {
        FString ResponseStr = Bridge->ExecuteCommand(CommandType, JsonObject->GetObjectField(TEXT("params")));
        
        UE_LOG(LogTemp, Display, TEXT("MCPServerRunnable: Sending response: %s"), *ResponseStr);
        
        FTCHARToUTF8 ConvertedResponse(*ResponseStr);
        int32 ResponseLength = ConvertedResponse.Length();
        
        // Send the 4-byte length prefix first (little-endian)
        uint8 LengthBytes[4];
        LengthBytes[0] = (ResponseLength >> 0) & 0xFF;
        LengthBytes[1] = (ResponseLength >> 8) & 0xFF;
        LengthBytes[2] = (ResponseLength >> 16) & 0xFF;
        LengthBytes[3] = (ResponseLength >> 24) & 0xFF;
        
        int32 BytesSent = 0;
        if (!Client->Send(LengthBytes, sizeof(LengthBytes), BytesSent))
        {
            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to send response length"));
            return;
        }
        
        // Then send the response payload
        if (!Client->Send((uint8*)ConvertedResponse.Get(), ResponseLength, BytesSent))
        {
            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to send response payload"));
        }
    }
    else
    {
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Missing 'type' field in command"));
    }
} 