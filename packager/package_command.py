import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional
import urllib.request
from . import macos_utils
from .sitecustomize import sitecustomize_py

mobile_pypi_url = "https://pypi.flet.dev"

default_site_packages_dir = "site-packages"
site_packages_env_var = "serious_python_site_packages"
flutter_packages_flutter_env_var = "SERIOUS_PYTHON_FLUTTER_PACKAGES"
allow_source_distros_env_var = "SERIOUS_PYTHON_ALLOW_SOURCE_DISTRIBUTIONS"

platforms = {
    "Android": {
        "arm64-v8a": {"tag": "android-24-arm64-v8a", "mac_ver": ""},
        "armeabi-v7a": {"tag": "android-24-armeabi-v7a", "mac_ver": ""},
        "x86_64": {"tag": "android-24-x86_64", "mac_ver": ""},
        "x86": {"tag": "android-24-x86", "mac_ver": ""},
    },
    "Darwin": {
        "arm64": {"tag": "", "mac_ver": "arm64"},
        "x86_64": {"tag": "", "mac_ver": "x86_64"},
    },
    "Windows": {
        "": {"tag": "", "mac_ver": ""},
    },
    "Linux": {
        "": {"tag": "", "mac_ver": ""},
    },
}

junk_files_desktop = [
    "**.c",
    "**.h",
    "**.cpp",
    "**.hpp",
    "**.typed",
    "**.pyi",
    "**.pxd",
    "**.pyx",
    "**.a",
    "**.pdb",
    "__pycache__",
    "**/__pycache__",
]
junk_files_mobile = [
    *junk_files_desktop,
    "**.exe",
    "**.dll",
    "bin",
    "**/bin",
]


class PackageCommand:
    def __init__(self):
        self._verbose = False
        self._build_dir: Optional[Path] = None

    def run(
        self,
        *,
        source_dir: Optional[str] = None,
        platform: str,
        arch: list,
        requirements: list,
        asset: Optional[str] = None,
        exclude: list,
        skip_site_packages: bool = False,
        compile_app: bool = False,
        compile_packages: bool = False,
        cleanup: bool = False,
        cleanup_app: bool = False,
        cleanup_app_files: list,
        cleanup_packages: bool = False,
        cleanup_package_files: list,
        verbose: bool = False,
    ) -> None:
        print("运行package命令")
        if source_dir is None:
            print("错误: 未提供源目录")
            sys.exit(1)

        try:
            current_path = Path.cwd()

            # args
            source_dir_path: Optional[str] = source_dir
            arch_arg: list = arch
            asset_path: Optional[str] = asset
            skip_site_packages: bool = skip_site_packages
            compile_app: bool = compile_app
            compile_packages: bool = compile_packages
            cleanup_app: bool = cleanup_app
            cleanup_app_files: list = cleanup_app_files
            cleanup_packages: bool = cleanup_packages
            cleanup_package_files: list = cleanup_package_files
            self._verbose = verbose

            if not Path(source_dir_path).is_absolute():
                source_dir_path = str(current_path / source_dir_path)

            source_dir = Path(source_dir_path)

            if platform not in platforms:
                sys.stderr.write(f"未知平台: {platform}\n")
                sys.exit(2)

            if not source_dir.exists():
                sys.stderr.write("源目录不存在.\n")
                sys.exit(2)

            is_mobile = platform in ("iOS", "Android")

            junk_files = junk_files_mobile if is_mobile else junk_files_desktop

            # Extra indexes
            extra_pypi_indexes = [mobile_pypi_url]
            print(f"额外的PyPi索引: {extra_pypi_indexes}")

            # ensure standard Dart/Flutter "build" directory exists
            self._build_dir = current_path / "build"
            if not self._build_dir.exists():
                self._build_dir.mkdir()

            # asset path
            if asset_path is None:
                asset_path = "build/app.zip"
            elif asset_path.startswith("/") or asset_path.startswith("\\"):
                asset_path = asset_path[1:]

            # create dest dir
            dest = current_path / asset_path
            dest_dir = dest.parent
            if not dest_dir.exists():
                print(f"新建资产目录: {dest_dir}")
                dest_dir.mkdir(parents=True, exist_ok=True)

            # create temp dir
            temp_dir = Path(tempfile.mkdtemp(prefix="serious_python_temp"))
            print(f"新建临时目录: {temp_dir}")

            # copy app to a temp dir
            print(f"正在复制 {source_dir} -> {temp_dir}")
            self.copy_directory(
                source_dir, temp_dir, str(source_dir),
                [s.strip() for s in exclude],
            )

            # compile all python code
            if compile_app:
                print("正在编译Python源文件...")
                subprocess.run([sys.executable, "-m", "compileall", "-b", str(temp_dir)])

                self.verbose("正在删除原始 .py 文件...")
                self.cleanup_dir(temp_dir, ["**.py"])

            # cleanup
            if cleanup_app or cleanup:
                al_junk_files = [*junk_files, *cleanup_app_files]
                if self._verbose:
                    self.verbose(
                        f"删除不必要的app文件和目录: {al_junk_files}"
                    )
                else:
                    print("正在清理app")
                self.cleanup_dir(temp_dir, al_junk_files)

            # install requirements
            if requirements and not skip_site_packages:
                site_packages_root = None

                if site_packages_env_var in os.environ:
                    site_packages_root = os.environ[site_packages_env_var]
                if site_packages_root is None or site_packages_root == "":
                    site_packages_root = str(temp_dir / "site-packages")

                if Path(site_packages_root).exists():
                    for f in Path(site_packages_root).iterdir():
                        if not f.name.startswith("."):
                            shutil.rmtree(str(f))

                flutter_packages_copied = False
                # invoke pip for every platform arch
                for arch_key, arch_value in platforms[platform].items():
                    if arch_arg and arch_key not in arch_arg:
                        continue
                    site_packages_dir = None
                    pip_env = None
                    sitecustomize_dir: Optional[Path] = None

                    try:
                        # customized pip
                        # create temp dir with sitecustomize.py for mobile and web
                        sitecustomize_dir = Path(
                            tempfile.mkdtemp(prefix="serious_python_sitecustomize")
                        )
                        if not sitecustomize_dir.exists():
                            sitecustomize_dir.mkdir(parents=True, exist_ok=True)
                        sitecustomize_path = (
                            sitecustomize_dir / "sitecustomize.py"
                        )
                        if self._verbose:
                            self.verbose(
                                f"已在 {sitecustomize_path} 配置平台 {platform}/{arch_key} 的 sitecustomize.py"
                            )
                        else:
                            print(
                                f"已配置平台 {platform}/{arch_key} 的 sitecustomize.py"
                            )

                        sitecustomize_path.write_text(
                            sitecustomize_py.replace(
                                "{platform}", platform if arch_value["tag"] else ""
                            )
                            .replace("{tag}", arch_value["tag"])
                            .replace("{mac_ver}", arch_value["mac_ver"])
                        )

                        pip_env = {
                            "PYTHONPATH": sitecustomize_dir,
                            # Prevent importing user-site packages (e.g. ~/.local/.../site-packages)
                            # which can shadow bundled pip in build Python.
                            "PYTHONNOUSERSITE": "1",
                        }

                        if arch_key:
                            site_packages_dir = str(
                                Path(site_packages_root) / arch_key
                            )
                        else:
                            site_packages_dir = site_packages_root
                        if not Path(site_packages_dir).exists():
                            Path(site_packages_dir).mkdir(parents=True, exist_ok=True)
                        print(
                            f"使用 uv 将 {requirements} 安装到 {site_packages_dir}"
                        )

                        pip_args = []

                        if is_mobile:
                            pip_args.extend(["--only-binary", ":all:"])
                            if allow_source_distros_env_var in os.environ:
                                pip_args.extend([
                                    "--no-binary",
                                    os.environ[allow_source_distros_env_var],
                                ])

                        for index in extra_pypi_indexes:
                            pip_args.extend(["--extra-index-url", index])

                        subprocess.run(
                            [
                                "uv",
                                "pip",
                                "install",
                                "--upgrade",
                                *pip_args,
                                "--target",
                                site_packages_dir,
                                *requirements,
                                "--index-strategy",
                                "unsafe-best-match"
                            ],
                            env={**os.environ, **{k: str(v) for k, v in pip_env.items()}} if pip_env else None,
                        )

                        # move $site_packages_dir/flutter if env var is defined
                        if flutter_packages_flutter_env_var in os.environ:
                            flutter_packages_root = os.environ[
                                flutter_packages_flutter_env_var
                            ]
                            flutter_packages_root_dir = Path(flutter_packages_root)
                            site_packages_flutter_dir = (
                                Path(site_packages_dir) / "flutter"
                            )
                            if site_packages_flutter_dir.exists():
                                if not flutter_packages_copied:
                                    print(
                                        f"正在将Flutter包复制到 {flutter_packages_root}"
                                    )
                                    if not flutter_packages_root_dir.exists():
                                        flutter_packages_root_dir.mkdir(
                                            parents=True, exist_ok=True
                                        )
                                    self.copy_directory(
                                        site_packages_flutter_dir,
                                        flutter_packages_root_dir,
                                        str(site_packages_flutter_dir),
                                        [],
                                    )
                                    flutter_packages_copied = True
                                shutil.rmtree(str(site_packages_flutter_dir))

                        # compile packages
                        if compile_packages:
                            print(
                                f"正在编译应用包 {site_packages_dir}"
                            )
                            subprocess.run(
                                [sys.executable, "-m", "compileall", "-b", site_packages_dir]
                            )

                            self.verbose("删除原始 .py 文件")
                            self.cleanup_dir(
                                Path(site_packages_dir), ["**.py"]
                            )

                        # cleanup packages
                        if cleanup_packages or cleanup:
                            al_junk_files = [*junk_files, *cleanup_package_files]
                            if self._verbose:
                                self.verbose(
                                    f"删除不必要的包文件和目录: {al_junk_files}"
                                )
                            else:
                                print("清理已安装的包")
                            self.cleanup_dir(
                                Path(site_packages_dir), al_junk_files
                            )
                    finally:
                        if sitecustomize_dir is not None and sitecustomize_dir.exists():
                            self.verbose(
                                f"删除 sitecustomize 目录 {sitecustomize_dir}"
                            )
                            shutil.rmtree(str(sitecustomize_dir))

                if platform == "Darwin":
                    macos_utils.merge_macos_site_packages(
                        str(Path(site_packages_root) / "arm64"),
                        str(Path(site_packages_root) / "x86_64"),
                        str(Path(site_packages_root)),
                        self._verbose,
                    )

                # synchronize pod
                sync_sh = (
                    Path(site_packages_root) / ".pod" / "sync_site_packages.sh"
                )
                if sync_sh.exists():
                    self.run_exec("/bin/sh", [str(sync_sh)])

            # create archive
            print(
                f"从临时目录创建应用存档 {dest}"
            )
            self.zip_directory_posix(temp_dir, dest)

            # create hash file
            print(f"将应用存档哈希写入 {dest}.hash")
            Path(f"{dest}.hash").write_text(self.calculate_file_hash(str(dest)))
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if temp_dir is not None and temp_dir.exists():
                print("删除临时目录")
                shutil.rmtree(str(temp_dir))

    def copy_directory(
        self,
        source: Path,
        destination: Path,
        root_dir: str,
        exclude_list: list,
    ) -> None:
        for entity in source.iterdir():
            rel_path = str(Path(entity).relative_to(root_dir))
            if rel_path in exclude_list:
                continue
            if entity.is_dir():
                new_directory = destination / entity.name
                new_directory.mkdir(exist_ok=True)
                self.copy_directory(
                    entity.resolve(), new_directory, root_dir, exclude_list
                )
            elif entity.is_file():
                shutil.copy2(str(entity), str(destination / entity.name))

    def cleanup_dir(self, directory: Path, filesGlobs: list) -> None:
        self.verbose(f"清理目录 {directory}: {filesGlobs}")
        self.cleanup_dir_recursive(directory, filesGlobs)

    def cleanup_dir_recursive(self, directory: Path, globs: list) -> bool:
        emptyDir = True
        for entity in list(directory.iterdir()):
            if any(
                fnmatch.fnmatch(
                    str(entity).replace("\\", "/"), g.replace("\\", "/")
                )
                for g in globs
            ) and entity.exists():
                self.verbose(f"删除 {entity}")
                if entity.is_dir():
                    shutil.rmtree(str(entity))
                else:
                    entity.unlink()
            elif entity.is_dir():
                if self.cleanup_dir_recursive(entity, globs):
                    self.verbose(f"删除空目录 {entity}")
                    entity.rmdir()
                else:
                    emptyDir = False
            else:
                emptyDir = False
        return emptyDir

    def run_exec(
        self,
        execPath: str,
        args: list,
        environment: Optional[dict] = None,
    ) -> int:
        env = os.environ.copy()
        if environment:
            for k, v in environment.items():
                if isinstance(v, Path):
                    env[k] = str(v)
                else:
                    env[k] = str(v)
            if "PYTHONPATH" in environment:
                env["PYTHONPATH"] = str(environment["PYTHONPATH"])

        proc = subprocess.Popen(
            [execPath, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        for line in proc.stdout:
            self.verbose(line.strip())

        stdout, stderr_text = proc.communicate()

        if proc.returncode != 0:
            sys.stderr.write(stderr_text)
            sys.exit(1)
        return proc.returncode

    def zip_directory_posix(self, source: Path, dest: Path) -> None:
        with zipfile.ZipFile(str(dest), "w", zipfile.ZIP_DEFLATED) as zf:
            for entity in source.rglob("*"):
                if not entity.is_file():
                    continue
                relativePath = entity.relative_to(source)
                # Convert to POSIX path
                posixPath = "/".join(relativePath.parts)
                zf.write(str(entity), posixPath)

    def calculate_file_hash(self, path: str) -> str:
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        return digest

    def verbose(self, text: str) -> None:
        if self._verbose:
            print(f"VERBOSE: {text}")
