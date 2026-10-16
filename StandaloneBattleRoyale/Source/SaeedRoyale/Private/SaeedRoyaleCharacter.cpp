#include "SaeedRoyaleCharacter.h"

#include "GameFramework/Controller.h"
#include "Components/InputComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"
#include "TimerManager.h"

ASaeedRoyaleCharacter::ASaeedRoyaleCharacter()
{
    PrimaryActorTick.bCanEverTick = false;
    bReplicates = true;
    SetReplicateMovement(true);
}

void ASaeedRoyaleCharacter::BeginPlay()
{
    Super::BeginPlay();
    if (HasAuthority())
    {
        Health = MaxHealth;
    }
}

void ASaeedRoyaleCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    Super::SetupPlayerInputComponent(PlayerInputComponent);
    check(PlayerInputComponent);

    PlayerInputComponent->BindAxis(TEXT("MoveForward"), this, &ASaeedRoyaleCharacter::MoveForward);
    PlayerInputComponent->BindAxis(TEXT("MoveRight"), this, &ASaeedRoyaleCharacter::MoveRight);
    PlayerInputComponent->BindAxis(TEXT("Turn"), this, &APawn::AddControllerYawInput);
    PlayerInputComponent->BindAxis(TEXT("LookUp"), this, &APawn::AddControllerPitchInput);
    PlayerInputComponent->BindAction(TEXT("Jump"), IE_Pressed, this, &ACharacter::Jump);
    PlayerInputComponent->BindAction(TEXT("Jump"), IE_Released, this, &ACharacter::StopJumping);
    PlayerInputComponent->BindAction(TEXT("Fire"), IE_Pressed, this, &ASaeedRoyaleCharacter::Fire);
}

void ASaeedRoyaleCharacter::MoveForward(float Value)
{
    if (Controller && !bEliminated && FMath::Abs(Value) > KINDA_SMALL_NUMBER)
    {
        const FRotator YawRotation(0.0f, Controller->GetControlRotation().Yaw, 0.0f);
        AddMovementInput(FRotationMatrix(YawRotation).GetUnitAxis(EAxis::X), Value);
    }
}

void ASaeedRoyaleCharacter::MoveRight(float Value)
{
    if (Controller && !bEliminated && FMath::Abs(Value) > KINDA_SMALL_NUMBER)
    {
        const FRotator YawRotation(0.0f, Controller->GetControlRotation().Yaw, 0.0f);
        AddMovementInput(FRotationMatrix(YawRotation).GetUnitAxis(EAxis::Y), Value);
    }
}

void ASaeedRoyaleCharacter::Fire()
{
    if (bEliminated || bFireOnCooldown)
    {
        return;
    }

    ServerFire();
    bFireOnCooldown = true;
    GetWorldTimerManager().SetTimer(FireCooldownTimer, [this]()
    {
        bFireOnCooldown = false;
    }, FireInterval, false);
}

void ASaeedRoyaleCharacter::ServerFire_Implementation()
{
    if (bEliminated || !Controller)
    {
        return;
    }

    FVector ViewLocation;
    FRotator ViewRotation;
    Controller->GetPlayerViewPoint(ViewLocation, ViewRotation);

    const FVector TraceEnd = ViewLocation + ViewRotation.Vector() * WeaponRange;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(SaeedRoyaleWeaponTrace), true, this);
    Params.AddIgnoredActor(this);

    if (GetWorld()->LineTraceSingleByChannel(Hit, ViewLocation, TraceEnd, ECC_Visibility, Params))
    {
        if (AActor* HitActor = Hit.GetActor())
        {
            UGameplayStatics::ApplyDamage(HitActor, WeaponDamage, Controller, this, nullptr);
        }
    }
}

float ASaeedRoyaleCharacter::TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser)
{
    if (!HasAuthority() || bEliminated || DamageAmount <= 0.0f)
    {
        return 0.0f;
    }

    const float AppliedDamage = FMath::Min(Health, DamageAmount);
    Health = FMath::Clamp(Health - AppliedDamage, 0.0f, MaxHealth);

    if (Health <= 0.0f)
    {
        Eliminate();
    }

    ForceNetUpdate();
    return AppliedDamage;
}

void ASaeedRoyaleCharacter::Eliminate()
{
    if (!HasAuthority() || bEliminated)
    {
        return;
    }

    bEliminated = true;
    GetCharacterMovement()->DisableMovement();
    SetActorEnableCollision(false);
    ForceNetUpdate();
}

void ASaeedRoyaleCharacter::OnRep_Health()
{
    // Hook for health UI and hit feedback in the next milestone.
}

void ASaeedRoyaleCharacter::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ASaeedRoyaleCharacter, Health);
    DOREPLIFETIME(ASaeedRoyaleCharacter, bEliminated);
}
