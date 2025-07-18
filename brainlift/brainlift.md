# Singularity One - Project Brainlift

This document outlines the key design and implementation decisions for the game project "Singularity One", based on the brainstorming session in `gemini-convo-1.md`.

## 1. Game Title

The official title for the project is **Singularity One**.

## 2. Core Concept

*   **Genre:** Third-Person Puzzle/Exploration with Parkour elements.
*   **Setting:** A high-tech research facility where an experiment has gone wrong, creating a black hole.
*   **Protagonist:** The lead researcher who caused the disaster.
*   **Goal:** The player must navigate the physics-defying lab to deliver a payload of antimatter to the black hole's core to neutralize it before it grows too large and consumes everything.
*   **Antagonist:** The black hole itself, which acts as a physical manifestation of the protagonist's hubris and serves as the game's primary time limit.

## 3. Core Themes

The game will explore its themes subtly through environmental storytelling rather than direct exposition.

*   **Primary Theme:** The dangers of unchecked scientific ambition and the need for self-restraint and humility.
*   **Secondary Theme:** The power of sacrificial love as a path to redemption.
*   **Tertiary Theme:** The idea that one's own efforts are not always enough, and moments of grace or "blessings" (divine or otherwise) are needed to succeed. This is framed in a way true to real-life, to allow for player interpretation.

## 4. Gameplay & Mechanics

The core gameplay philosophy is to make the player feel "barely in control." The player's controls are stable and consistent, but the environment's physics are chaotic and unpredictable.

### a. Perspective

*   **Third-Person:** Chosen to give flexibility to switch to first person later.  First person may maximize immersion, psychological pressure, and the disorienting feeling of the physics shifts.

### b. Failure State

*   **No Traditional Death:** The player does not "die" from falling or taking damage in the traditional sense. There is no health bar that leads to a "Game Over" screen.
*   **Time is the Only Enemy:** The single failure state is a global timer. If the player cannot reach the objective before the timer runs out (representing the black hole's growth), they fail.
*   **Mistakes Cost Time:** Falling off a platform or making an error results in losing time, as the player must recover and get back on track.

### c. Player Health & Damage

*   **Suit Integrity System:** Instead of a health bar, the player has a "Suit Integrity" meter.
*   **Consequences of Damage:** Taking damage from long falls or environmental hazards permanently lowers the suit's integrity.
    *   **High Integrity:** The suit functions perfectly.
    *   **Medium Integrity:** Cosmetic glitches appear (HUD flickers, static). Minor gameplay handicaps are introduced (e.g., slower energy recharge).
    *   **Low Integrity:** The suit becomes unstable, causing random, brief physics glitches for the player (e.g., sudden visual refraction, a momentary gravity lurch). This makes traversal more difficult and tense.

### d. Core Physics Anomalies

These are the primary mechanics the player will encounter and use to navigate the world.

*   **Gravity Shifting (Implemented as World Rotation):**
    *   Gravity itself remains constant (always "down").
    *   The entire world/level rotates around the player, making walls the new floors.
    *   This approach was chosen for implementation stability after prototyping revealed camera control issues with dynamically changing the gravity vector.
*   **Light Refraction Fields:**
    *   Areas where light is distorted, making the visual path differ from the actual physical path.
    *   Players must learn to trust their suit's instruments (e.g., a HUD guideline) over their own eyes to navigate these zones.
*   **Medium Viscosity Changes:**
    *   Areas where the air becomes thick like water or thin and unsubstantial.
    *   This affects player movement speed, jump height, and the trajectory of objects.
*   **Other Brainstormed Anomalies:** Time Dilation, Localized Inertial Dampening, Entangled Objects.

### e. Multiplayer: "The Echoes System"

*   **Asynchronous & Unconventional:** The game is a single-player experience at its core, but with a unique, hidden multiplayer component.
*   **Echoes of Other Players:** Players can see faint, ghostly "echoes" of other players who are going through the same space in their own game.
*   **Hidden Mechanics:** The interactions are non-deterministic and hidden from the player. Players are not explicitly told that another player's action helped them.
*   **Sacrifice & Blessings:** When a player makes a sacrifice, it may create a "blessing" in another player's world—a moment of stability, a briefly opened path, etc. This feels like a moment of grace or luck, not a multiplayer transaction.

### f. The Sacrifice Mechanic

*   **Permanent Suit Deterioration:** To make sacrifices meaningful, they come at a permanent cost to the player's abilities.
*   **Example:** A player might choose to divert power from their suit to help their family (who are trapped elsewhere). This could permanently reduce their maximum sprint speed, making the rest of the game more challenging and costing them cumulative time. This makes the choice a weighty, tactical one with lasting consequences.

## 5. Narrative & Storytelling

*   **Show, Don't Tell:** The story is pieced together through environmental clues.
*   **Environmental Narrative:** The protagonist's past hubris and the warnings of concerned colleagues are revealed through audio logs, emails, and notes found throughout the facility.
*   **Ambiguity:** Events that could be interpreted as "miracles" or "answered prayers" are also given plausible in-world scientific explanations, allowing the player to form their own interpretation of the events. 
