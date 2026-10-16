#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "SaeedRoyaleCharacter.generated.h"

UCLASS()
class SAEEDROYALE_API ASaeedRoyaleCharacter : public ACharacter
{
    GENERATED_BODY()

public:
    ASaeedRoyaleCharacter();
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
    virtual float TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    UFUNCTION(BlueprintPure, Category = "Saeed Royale|Health")
    float GetHealth() const { return Health; }

    UFUNCTION(BlueprintPure, Category = "Saeed Royale|Health")
    bool IsEliminated() const { return bEliminated; }

protected:
    virtual void BeginPlay() override;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Saeed Royale|Health", meta = (ClampMin = "1.0"))
    float MaxHealth = 100.0f;

    UPROPERTY(ReplicatedUsing = OnRep_Health, VisibleAnywhere, BlueprintReadOnly, Category = "Saeed Royale|Health")
    float Health = 100.0f;

    UPROPERTY(Replicated, VisibleAnywhere, BlueprintReadOnly, Category = "Saeed Royale|Health")
    bool bEliminated = false;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Saeed Royale|Combat", meta = (ClampMin = "100.0"))
    float WeaponRange = 15000.0f;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Saeed Royale|Combat", meta = (ClampMin = "1.0"))
    float WeaponDamage = 25.0f;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Saeed Royale|Combat", meta = (ClampMin = "0.05"))
    float FireInterval = 0.2f;

    UFUNCTION()
    void OnRep_Health();

    UFUNCTION(Server, Reliable)
    void ServerFire();

    void MoveForward(float Value);
    void MoveRight(float Value);
    void Fire();
    void Eliminate();

    FTimerHandle FireCooldownTimer;
    bool bFireOnCooldown = false;
};
