import os

ROOT = "."

def walk(dir_path, prefix=""):
    entries = sorted(os.listdir(dir_path))
    for i, name in enumerate(entries):
        path = os.path.join(dir_path, name)
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "

        print(prefix + connector + name)

        if os.path.isdir(path):
            extension = "    " if is_last else "│   "
            walk(path, prefix + extension)

def main():
    print("SITE DIRECTORY TREE\n")
    print(".")
    walk(ROOT)

if __name__ == "__main__":
    main()