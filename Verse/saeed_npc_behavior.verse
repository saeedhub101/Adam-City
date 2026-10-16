using { /Fortnite.com/AI }
using { /Fortnite.com/AI/movement_types }
using { /Fortnite.com/Characters }
using { /Verse.org/Random }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/SpatialMath }

# Starter behavior for Saeed as a custom NPC.
# Attach this script to an NPC Character Definition configured for Verse Behavior.
# Compile and playtest in UEFN before using it in an island.
saeed_npc_behavior<public> := class(npc_behavior):

    # Random horizontal offset from the NPC's spawn position, in centimeters.
    @editable
    WanderRadius:float = 300.0

    # Pause after reaching a navigation target.
    @editable
    WaitDuration:float = 3.0

    # NPC navigation currently requires movement type, reach radius, and partial-path policy.
    ReachRadius:float = 100.0

    OnBegin<override>()<suspends>:void=
        if:
            Agent := GetAgent[]
            Character := Agent.GetFortCharacter[]
            Navigatable := Character.GetNavigatable[]
        then:
            SpawnPosition := Character.GetTransform().Translation
            loop:
                Offset := vector3{
                    X := GetRandomFloat(-WanderRadius, WanderRadius),
                    Y := GetRandomFloat(-WanderRadius, WanderRadius),
                    Z := 0.0
                }
                TargetPosition := SpawnPosition + Offset
                NavigationTarget := MakeNavigationTarget(TargetPosition)
                Result := Navigatable.NavigateTo(
                    NavigationTarget,
                    movement_types.Walking,
                    ReachRadius,
                    false
                )
                if (Result = navigation_result.Reached):
                    Navigatable.Wait(?Duration := WaitDuration)
                else:
                    Navigatable.Wait(?Duration := 1.0)
