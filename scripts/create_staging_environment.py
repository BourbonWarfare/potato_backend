from pathlib import Path
import os
import shutil


def _validate() -> bool:
    acceptable = input('Ok? [Y/n]')
    if acceptable.lower() not in ('y', 'yes', ''):
        print('Aborting. No changes made.')
        return False
    return True


def main():
    print('Creating staging environment for ARMA 3 servers')
    main_arma_server_dir = Path('B:/gameservers/arma')
    staging_dir = main_arma_server_dir.parent / 'staging_arma'
    print(f'Copying from {main_arma_server_dir} to {staging_dir}')
    if not _validate():
        return

    if os.path.exists(staging_dir):
        print(f'Staging directory {staging_dir} already exists. Removing it.')
        if not _validate():
            return
        shutil.rmtree(staging_dir, ignore_errors=True)

    print(f'Copying files from {main_arma_server_dir} to {staging_dir}')
    try:
        shutil.copytree(main_arma_server_dir, staging_dir, dirs_exist_ok=True, symlinks=True, ignore_dangling_symlinks=True)
    except Exception as e:
        print(f'An error occurred while copying files: {e}')
        return

    # Make this path not exist anymore so we don't accidentally manipulate prod
    del main_arma_server_dir

    print(f'Staging environment created at {staging_dir}')
    print('Removing all symlinks to prod files...')
    for root, _, files in os.walk(staging_dir):
        for name in files:
            path = Path(root) / name
            if path.is_symlink():
                print(f'Removing: {path}')
                path.unlink()

    print('Creating explicit symlinks to foreign folders')
    os.symlink(staging_dir / 'missions' / 'main', staging_dir / 'main' / 'mpmissions')
    os.symlink(staging_dir / 'missions' / 'alternate', staging_dir / 'alternate' / 'mpmissions')

    print('Staging environment setup complete.')


if __name__ == '__main__':
    main()
