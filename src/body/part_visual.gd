class_name PartVisual
extends Resource
## A piece of visible hardware a part adds to the body (docs/design.md §3.3:
## "they change how you look"). Mounted on a socket of the operative model
## (BodyAppearance.SOCKETS: a bone name plus an offset). Either a scene
## (a modelled piece) or, until the piece is modelled, a simple shape so the
## mount point and size are visible on the body-status screen.

enum Shape { NONE, BOX, CAPSULE, CYLINDER }

## Socket on the operative body, e.g. &"spine_upper", &"forearm.L", &"head".
@export var socket: StringName = &"chest"
@export var scene: PackedScene
## The scene was modelled on the whole operative in its rest pose (model
## space, raw_assets/augments/passives/): each mesh in it is named
## "B_<bone>__<piece>" (bone with "_L"/"_R" for ".L"/".R") and goes on that
## bone, so the pieces follow the body as it moves. `socket` is ignored.
@export var model_space: bool = false
@export var shape: Shape = Shape.NONE
@export var size: Vector3 = Vector3(0.05, 0.05, 0.05)
@export var offset: Vector3 = Vector3.ZERO
@export var rotation_deg: Vector3 = Vector3.ZERO
## Plates read as black carapace; hardware as gunmetal; glow as the seam light.
@export_enum("plate", "hardware", "glow") var finish: String = "hardware"
## Shown in first person on the arms (sockets on the forearms/hands only).
@export var first_person: bool = false
