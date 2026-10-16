using { /Fortnite.com/AI }
using { /Fortnite.com/Characters }
using { /Verse.org/Random }
using { /Verse.org/Simulation }

# Starter behavior for a custom Saeed NPC.
# Attach this script to an NPC Character Definition configured for Verse Behavior.
# Compile and playtest in the target UEFN version before using in a published island.
saeed_npc_behavior<public> := class(npc_behavior):

    # Maximum horizontal wandering offset in centimeters from the current position.
    @editable
    WanderRadius:float = 300.0

    # Pause after reaching a navigation target.
    @editable
    WaitDuration:float = 3.0

    # Radius at which navigation considers a target reached.
    @editable
    ReachRadius:float = 100.0

    OnBegin<override>()<suspends>:void=
        if:
            Agent := GetAgent[]
            Character := Agent.GetFortCharacter[]
            Navigatable := Character.GetNavigatable[]
        then:
            loop:
                CurrentPosition := Character.GetTransform().Translation
                Offset := vector3{
                    X := GetRandomFloat(-WanderRadius, WanderRadius),
                    Y := GetRandomFloat(-WanderRadius, WanderRadius),
                    Z := 0.0
                }
                TargetPosition := CurrentPosition + Offset
                NavigationTarget := MakeNavigationTarget(TargetPosition)
                Result := Navigatable.NavigateTo(
                    NavigationTarget,
                    ?ReachRadius := ReachRadius
                )
                if (Result = navigation_result.Reached):
                    Navigatable.Wait(?Duration := WaitDuration)
                else:
                    # Brief pause before choosing a new target if navigation fails.
                    Navigatable.Wait(?Duration := 1.0)

    OnEnd<override>():void=
        # No persistent external resources are created by this behavior.
        return
