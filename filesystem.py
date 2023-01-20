class Filesystem():
    def __init__(self):
        self.current_folder = None

    def read(self):
        return self.current_folder.read()

    def open_all(self):
        self.current_folder.open_all()

    def close_all(self):
        self.current_folder.close_all()

    def create_folder(self, name, description=''):
        folder = Folder(name, description)
        self.current_folder = folder
        return folder

    def set_current_folder(self, folder):
        self.current_folder = folder

    def get_current_folder(self):
        return self.current_folder

    def set_description(self, description):
        self.description = description

    def find_folder(self, path):
        if path == self.current_folder.name:
            return self.current_folder

        folder = self.current_folder
        rel_path = path.split(self.current_folder.name)[1]

        for name in rel_path.split('/'):
            if name == '..':
                folder = folder.parent
            else:
                for f in folder.folders:
                    if f.name == name:
                        folder = f
                        break

        return folder

    def open(self):
        self.current_folder.open()

    def close(self):
        self.current_folder.close()

class Folder:
    def __init__(self, name, description=''):
        self.name = name
        self.description = description
        self.files = []
        self.folders = []
        self.is_open = False

    def set_description(self, description):
        self.description = description

    def add_file(self, file):
        self.files.append(file)

    def add_folder(self, folder):
        folder.parent = self
        self.folders.append(folder)

    def open(self):
        self.is_open = True

    def open_all(self):
        self.open()
        for folder in self.folders:
            folder.open_all()

    def close(self):
        self.is_open = False
        for folder in self.folders:
            folder.close()

    def close_all(self):
        self.close()
        for folder in self.folders:
            folder.close_all()

    def read(self, indent=0):
        str = '  ' * indent + f'{self.name.upper()}\n'

        if self.is_open:
            indent += 1
            for folder in self.folders:
                str += folder.read(indent)

            for file in self.files:
                str += '  ' * indent + file.read() + '\n'

        return str

class File:
    def __init__(self, name, description=''):
        self.name = name
        self.description = description

    def set_description(self, description):
        self.description = description

    def read(self):
        return f'{self.name}'


if __name__ == '__main__':
    import os

    for root, dirs, files in os.walk('repos/bootstrap', topdown=True):
        print(root, dirs, files)
        for name in files:
            filename = os.path.join(root, name)