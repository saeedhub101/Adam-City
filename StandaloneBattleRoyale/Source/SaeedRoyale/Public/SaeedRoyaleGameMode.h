#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "SaeedRoyaleGameMode.generated.h"

UCLASS()
class SAEEDROYALE_API ASaeedRoyaleGameMode : public AGameModeBase
{
    GENERATED_BODY()

public:
    ASaeedRoyaleGameMode();

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Saeed Royale|Match", meta = (ClampMin = "2", ClampMax = "100"))
    int32 MaxPlayers = 100;
};
