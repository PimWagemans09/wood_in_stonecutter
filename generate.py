import pathlib
import shutil
import json
import copy
from typing import Tuple
import argparse


try:
    with open("default_world.txt") as file:
        default_world = file.read().rstrip("\n")
except FileNotFoundError:
    default_world = ""

arg_parser = argparse.ArgumentParser()

arg_parser.add_argument(
    "--place-in-world",
    action="store_true",
    help='copies the generated zip file into the datapacks directory specified in the "default_world.txt" or in the "--world"  argument if that\'s present',
)
arg_parser.add_argument(
    "--world",
    help='if the "--place-in-world" argument is present the zip file will be placed in the datapacks directory specified in "WORLD"',
)
arg_parser.add_argument(
    "--no-file-names",
    action="store_true",
    help="if this argument is present the program wont print what files it is generating",
)

args = arg_parser.parse_args()

world_datapack_dir = pathlib.Path(default_world)

if args.world != None:
    world_datapack_dir = pathlib.Path(args.world)

displayed_too_many_files_warning = False

WOODTYPES: list[list[str | None]] = [
    ["oak", "log", "wood", "boat"],
    ["spruce", "log", "wood", "boat"],
    ["bamboo", "block", None, "raft"],
    ["birch", "log", "wood", "boat"],
    ["jungle", "log", "wood", "boat"],
    ["acacia", "log", "wood", "boat"],
    ["dark_oak", "log", "wood", "boat"],
    ["mangrove", "log", "wood", "boat"],
    ["cherry", "log", "wood", "boat"],
    ["crimson", "stem", "hyphae", None],
    ["warped", "stem", "hyphae", None],
    ["pale_oak", "log", "wood", "boat"],
]


def delete_contents_of_dir(pth: pathlib.Path):
    for child in pth.iterdir():
        if child.is_file():
            child.unlink()
        else:
            delete_contents_of_dir(child)
            child.rmdir()


def replace_woodtype_placeholders(
    string: str, woodtype: list[str | None]
) -> tuple[str, bool, bool, bool]:

    has_log_like_block = (not r"{WOODTYPE_LOGNAME}" in string) or (woodtype[1] != None)
    has_wood_like_block = (not r"{WOODTYPE_WOODNAME}" in string) or (
        woodtype[2] != None
    )
    has_boat_like_item = (not r"{WOODTYPE_BOATNAME}" in string) or (woodtype[3] != None)

    parsed_string = string

    parsed_string = parsed_string.replace(r"{WOODTYPE}", woodtype[0])

    if woodtype[1] != None:
        parsed_string = parsed_string.replace(r"{WOODTYPE_LOGNAME}", woodtype[1])

    if woodtype[2] != None:
        parsed_string = parsed_string.replace(r"{WOODTYPE_WOODNAME}", woodtype[2])

    if woodtype[3] != None:
        parsed_string = parsed_string.replace(r"{WOODTYPE_BOATNAME}", woodtype[3])

    return (parsed_string, has_log_like_block, has_wood_like_block, has_boat_like_item)


print("Clearing output directory...")
output_dir = pathlib.Path("./output").resolve()
delete_contents_of_dir(output_dir)

src_dir = pathlib.Path("./src").resolve()
template_dir = src_dir / "templates"

print("Copying base datapack to output...")
shutil.copytree(str(src_dir / "base_datapack"), str(output_dir), dirs_exist_ok=True)

recipe_dir = (
    output_dir / "wood_in_stonecutter" / "data" / "wood_in_stonecutter" / "recipe"
)
if not args.no_file_names:
    print("Generating files:")
else:
    print("Generating files...")
for template in template_dir.iterdir():
    with template.open() as template_file:
        template_data = json.load(template_file)
    for woodtype in WOODTYPES:

        parsed_template_name = replace_woodtype_placeholders(template.name, woodtype)
        if (
            parsed_template_name[1]
            and parsed_template_name[2]
            and parsed_template_name[3]
        ):
            output_file = recipe_dir / parsed_template_name[0]
        else:
            continue  # skip this template for this woodtype because this template uses a wood-like block, log-like block or a boat-like item that the recipe doesn't use

        if output_file.exists():
            base_file_name = output_file.stem
            base_file_extension = output_file.suffix
            for idx in range(2, 1001):
                new_file_name = base_file_name + "_" + str(idx) + base_file_extension
                output_file = recipe_dir / new_file_name
                idx += 1
                if not output_file.exists():
                    break

            if idx == 1001:
                print("too many files with the same name!")
                if not displayed_too_many_files_warning:
                    displayed_too_many_files_warning = True
                    print(
                        "  you seem to be generating more than a 1000 files with the same name.\n  to prevent infinite loops you can not generate more than a 1000 files with the same name\n  this message will be displayed for every file that you create over the limit"
                    )
                continue

        if not args.no_file_names:
            print(f"  - Generating: {output_file.name}")

        output_data = copy.deepcopy(template_data)
        parsed_template_ingredient = replace_woodtype_placeholders(
            template_data["ingredient"], woodtype
        )
        if (
            parsed_template_ingredient[1]
            and parsed_template_ingredient[2]
            and parsed_template_ingredient[3]
        ):
            output_data["ingredient"] = parsed_template_ingredient[0]
        else:
            continue  # skip this template for this woodtype because this template uses a wood-like block, log-like block or a boat-like item that the recipe doesn't use

        parsed_template_result = replace_woodtype_placeholders(
            template_data["result"]["id"], woodtype
        )
        if (
            parsed_template_result[1]
            and parsed_template_result[2]
            and parsed_template_result[3]
        ):
            output_data["result"]["id"] = parsed_template_result[0]
        else:
            continue  # skip this template for this woodtype because this template uses a wood-like block, log-like block or a boat-like item that the recipe doesn't use

        with output_file.open("w") as opened_output_file:
            json.dump(output_data, opened_output_file, indent=4)

print("Fixing bamboo...")  # TODO: dont hardcode this
with (recipe_dir / "bamboo_planks_from_stonecutting.json").open("r") as file:
    bamboo_plank_recipe_data = json.load(file)
bamboo_plank_recipe_data["result"]["count"] = 2
with (recipe_dir / "bamboo_planks_from_stonecutting.json").open("w") as file:
    json.dump(bamboo_plank_recipe_data, file, indent=4)

print("Creating zip archive...")
shutil.make_archive(
    str(output_dir / "wood_in_stonecutter"),
    "zip",
    str(output_dir / "wood_in_stonecutter"),
)


def place_in_dir():
    global world_datapack_dir, output_dir
    print("Placing zip archive in world datapacks directory...")
    if str(world_datapack_dir) == ".":
        print(
            '  Couldn\'t place the generated zip archive in the datapacks directory because:\n    -No file called "default_world.txt" containing a path to a datapacks directory was found\n    -No "--world <Path>"  argument containing a path to a datapacks directory was passed to the program'
        )
        return
    if (world_datapack_dir / "wood_in_stonecutter.zip").exists():
        try:
            (world_datapack_dir / "wood_in_stonecutter.zip").unlink()
        except:
            print(
                "  Couldn't delete old datapack file please make sure you have the datapack disabled if you have the world open"
            )
            return
    shutil.copy(
        output_dir / "wood_in_stonecutter.zip",
        world_datapack_dir / "wood_in_stonecutter.zip",
    )
    print(
        f'  Copied the generated zip archive to the world "{world_datapack_dir.parent.name}"'
    )


if args.place_in_world:
    place_in_dir()


print(
    "Done! The datapack can be found as a directory and as a zip archive in the output directory"
)
