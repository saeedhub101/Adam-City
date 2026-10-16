#include "SaeedRoyaleGameMode.h"
#include "SaeedRoyaleCharacter.h"

ASaeedRoyaleGameMode::ASaeedRoyaleGameMode()
{
    DefaultPawnClass = ASaeedRoyaleCharacter::StaticClass();
    bUseSeamlessTravel = true;
}
