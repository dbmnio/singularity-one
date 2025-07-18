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
						// Convert the byte array to a string for the JSON reader
						FString JsonString;
						FFileHelper::BufferToString(JsonString, MessagePayload.GetData(), MessagePayload.Num());

						TSharedPtr<FJsonObject> JsonObject;
						TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonString);

						if (FJsonSerializer::Deserialize(Reader, JsonObject) && JsonObject.IsValid())
						{
							ProcessMessage(InClientSocket, JsonObject);
						}
						else
						{
							UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to parse JSON message. Error: %s"), *Reader->GetErrorMessage());
						}
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

void FMCPServerRunnable::ProcessMessage(TSharedPtr<FSocket> Client, const TSharedPtr<FJsonObject>& JsonObject)
{
    if (!JsonObject.IsValid())
    {
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: ProcessMessage received an invalid JSON object."));
        return;
    }
	
    FString CommandType;
    if (!JsonObject->TryGetStringField(TEXT("command"), CommandType))
    {
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: JSON message does not contain a 'command' field."));
        return;
    }

    TSharedPtr<FJsonObject> Params = JsonObject->GetObjectField(TEXT("params"));

    // Execute the command on the game thread
    FString ResultString = Bridge->ExecuteCommand(CommandType, Params);

    // Send the response back to the client
    FTCHARToUTF8 Converter(*ResultString);
    int32 ResponseLength = Converter.Length();
    
    // Send the 4-byte length prefix first (little-endian)
    uint8 LengthBytes[4];
    LengthBytes[0] = (ResponseLength >> 0) & 0xFF;
    LengthBytes[1] = (ResponseLength >> 8) & 0xFF;
    LengthBytes[2] = (ResponseLength >> 16) & 0xFF;
    LengthBytes[3] = (ResponseLength >> 24) & 0xFF;
    
    int32 BytesSent = 0;
    Client->Send(LengthBytes, sizeof(LengthBytes), BytesSent);

    // Then send the response payload
    Client->Send((uint8*)Converter.Get(), ResponseLength, BytesSent);
} 