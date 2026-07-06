import pathlib
import shutil
import json
import argparse

with open("generation_info.json", "r") as f:
    generation_info = json.load(f)

arg_parser = argparse.ArgumentParser()

arg_parser.add_argument(
    "--no-file-names",
    action="store_true",
    help="if this argument is present the program wont print what files it is generating",
)

args = arg_parser.parse_args()

def delete_contents_of_dir(pth: pathlib.Path):
    for child in pth.iterdir():
        if child.is_file():
            child.unlink()
        else:
            delete_contents_of_dir(child)
            child.rmdir()


def replace_placeholders(string: str,) -> list[str|None]:
    results: list[str|None] = []
    for option_list in generation_info["options"]:
        temp_string = string
        for i in range(len(generation_info["placeholders"])):
            if "{%s}" % generation_info["placeholders"][i] not in temp_string:
                continue
            if option_list[i] is None:
                results.append(None)
                break
            temp_string = temp_string.replace("{%s}" % generation_info["placeholders"][i], option_list[i])
        else:
            results.append(temp_string)
    return results


def _replace_conditional_replacements_inner(data: dict, option_list:int):
    if "CONDITIONAL_REPLACEMENT" in data:
        placeholder = data["CONDITIONAL_REPLACEMENT"]
        placeholder_index = generation_info["placeholders"].index(placeholder)
        if generation_info["options"][option_list][placeholder_index] in data["conditions"]:
            return data["conditions"][generation_info["options"][option_list][placeholder_index]]
        else:
            return data["conditions"]["*"]
    else:
        return replace_conditional_replacements(data, option_list)


def replace_conditional_replacements(data: dict, option_list:int) -> dict:
    for key, value in data.items():
        if isinstance(value, dict):
            data[key] = _replace_conditional_replacements_inner(value,option_list)
        if isinstance(value, list):
            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    value[idx] = _replace_conditional_replacements_inner(item,option_list)

    return data


# print("Clearing output directory...")
output_dir = pathlib.Path(generation_info["dest_dir"]).resolve()
base_dir = pathlib.Path(generation_info["base_file_structure"]).resolve()
if (output_dir / base_dir.name).exists():
    delete_contents_of_dir(output_dir / base_dir.name)
    (output_dir / base_dir.name).rmdir()
if (output_dir / (base_dir.name + ".zip")).exists():
    (output_dir / (base_dir.name + ".zip")).unlink()

template_dir = pathlib.Path(generation_info["src_dir"]).resolve()

print("Copying base datapack to output...")
print(base_dir, output_dir)
shutil.copytree(str(base_dir), str(output_dir / base_dir.name), dirs_exist_ok=True)

generated_files_nr = 0

if not args.no_file_names:
    print("Generating files:")
else:
    print("Generating files...")
for src_subdir, out_subdir_raw in generation_info["src_dir_to_output_dir_mapping"].items():
    src_subdir = template_dir / src_subdir
    out_subdir = output_dir / base_dir.name / out_subdir_raw
    for template in src_subdir.iterdir():
        with template.open("r") as template_file:
            template_string = template_file.read()
        generated_files = replace_placeholders(template_string)
        generated_filenames = replace_placeholders(template.name)
        for idx, filename in enumerate(generated_filenames):
            if filename is None:
                continue
            if generated_files[idx] is None:
                continue
            if not args.no_file_names:
                print(f"  - {out_subdir_raw}/{generated_filenames[idx]}...")
            generated_file_data = json.loads(generated_files[idx])
            generated_file_data = replace_conditional_replacements(generated_file_data, idx)
            outfile = out_subdir / generated_filenames[idx]
            with open(outfile, "w") as out_file:
                json.dump(generated_file_data, out_file, indent=4)
            generated_files_nr += 1

print(f"Generated {generated_files_nr} files")

print("Creating zip archive...")
shutil.make_archive(
    str(output_dir / base_dir.name),
    "zip",
    str(output_dir / base_dir.name),
)

print("Done!")
