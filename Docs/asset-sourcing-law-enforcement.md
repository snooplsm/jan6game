# Law-Enforcement and Crowd-Control Asset Sourcing

Target: public-facing historical visualization/game assets. Use generic visual representations; do not encode operational security layouts, protective-glazing specifications, or person-specific protective procedures.

## Recommended Unreal character source

### LE Characters Pack (Fab)

- URL: https://www.fab.com/listings/3a04f4ae-579a-4a48-a0ba-5fb8aa65a95b
- Status: paid; user purchase/library authorization required
- Includes: modular police, riot-police, rapid-response, sheriff, and security variants
- Unreal fit: UE5, Epic/Manny-compatible, rigged, multiple LODs
- Planned use: visually customized generic Capitol Police-style uniforms without copying protected insignia or implying exact equipment assignments

### Modern Police / Sheriff Character (Fab)

- URL: https://www.fab.com/listings/c842132a-7ab5-4c3b-acbf-76794b18e7cd
- Status: paid; user purchase/library authorization required
- Includes: modular uniform, accessories, baton, animations, LODs, and 4K PBR textures
- Planned use: lower-scope alternative if a full character bundle is unnecessary

## Equipment candidates

### Riot Shield and Baton (CGTrader)

- URL: https://www.cgtrader.com/free-3d-models/various/various-models/riot-shield-and-baton
- Status: free listing; verify the downloadable license text before adding to source control
- Formats: OBJ, FBX, and Blender; textured
- Planned use: generic handheld prop meshes with Unreal collision and LODs added locally

Helmets and uniform equipment should preferably come from the selected modular Fab character pack so skeleton attachment points, materials, and scale remain consistent.

## Barrier candidates

### Crowd-Control Barrier (Cults / TraceParts)

- URL: https://cults3d.com/en/3d-model/game/crowd-control-barrier
- Status: free STL listing; verify commercial/game redistribution terms before importing
- Planned use: reference or conversion source for generic interlocking pedestrian barriers

### CC0 Construction Barrier (OpenGameArt)

- URL: https://opengameart.org/content/construction-barrier-3d
- License: listed as CC0; retain a local copy of the license page at acquisition time
- Format: Blender
- Planned use: generic temporary road/crowd-control prop

## Protective glazing

Create a generic Unreal laminated-security-glass material locally instead of acquiring a security-specific product model. It may visually use thick glass, edge tint, subtle layered reflections, and metal framing. Do not model real protective ratings, pane composition, attachment engineering, restricted placement, or presidential security procedures.

## Import checklist

1. User purchases or authorizes any paid Fab pack.
2. Save the exact license/receipt metadata outside the distributable game content.
3. Import into `/Game/Characters/LawEnforcement` or `/Game/Props/CrowdControl`.
4. Retarget characters to UE5 Manny/MetaHuman as applicable.
5. Add LOD, Nanite, collision, and material-instance validation.
6. Replace real agency insignia with project-cleared artwork unless usage rights are confirmed.
7. Place barriers only from publicly documented visual references; do not infer restricted security layouts.
