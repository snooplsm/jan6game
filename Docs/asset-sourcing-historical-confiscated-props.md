# Historical Confiscated-Prop Asset Sourcing

Scope: inert visual/reference props representing broad categories documented in official January 6 case records. These assets are not gameplay-ready weapons by default and must not include construction or activation instructions for incendiary or explosive devices.

## Ready for user library authorization

### Free Shotgun and Props (Fab)

- URL: https://www.fab.com/listings/0f1a0028-3886-4c8a-a52a-4e7443cd5de1
- Price shown: Free
- Format: Unreal Engine
- Status: user must add the listing to their Fab library and confirm the license shown at acquisition
- Planned folder: `/Game/Props/HistoricalEvidence/Firearms/Shotgun`
- Planned configuration: static/inert prop only; disable weapon Blueprint behavior if supplied

## Free candidates pending license verification

### Riot Shield and Baton (CGTrader)

- URL: https://www.cgtrader.com/free-3d-models/various/various-models/riot-shield-and-baton
- Price shown: Free
- Formats: OBJ, FBX, Blender
- Status: verify downloaded license terms before source-control inclusion
- Planned folder: `/Game/Props/CrowdControl/ShieldBaton`

## Model locally from generic public shapes

The following categories are better authored as generic low-risk static props so the project does not depend on unclear marketplace licensing or real product specifications:

- Wooden bat and plain metal/wood poles
- Flagpole and detached signpost variants
- Machete silhouette and generic utility knife
- Crossbow silhouette and inert bolt bundle
- Stun-device silhouette with no functional markings
- Smoke-device canister silhouette
- Ammunition-box and magazine silhouettes without internal/mechanical detail
- Fire extinguisher and wooden pallet
- Generic pepper/bear-spray canister with fictional labeling

## Excluded from functional implementation

- Molotov-cocktail components
- Pipe bombs or explosive-device internals
- Ignition, detonation, assembly, or chemical recipes

If required for a historical evidence display, incendiary/explosive categories may be represented only by a sealed evidence-box icon, placard, or highly generic inert silhouette.

## Import requirements

1. Record the acquisition URL, date, creator, and exact license.
2. Keep source receipts/licenses outside distributable game content.
3. Import into `/Game/Props/HistoricalEvidence` or `/Game/Props/CrowdControl`.
4. Strip scripts, firing systems, ammunition logic, damage logic, and muzzle/VFX behavior.
5. Generate collision and LODs suitable for static museum/environment display.
6. Use fictional serial numbers and markings.
7. Add an `InertHistoricalProp` gameplay tag before placement.
