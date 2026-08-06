from pathlib import Path
import base64
import io
import shutil
import tarfile

root = Path(__file__).resolve().parent
parts_dir = root / ".bootstrap"
payload = "".join(p.read_text(encoding="utf-8").strip() for p in sorted(parts_dir.glob("part*.txt")))
archive = base64.b64decode(payload)
with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
    for member in tar.getmembers():
        target = (root / member.name).resolve()
        if root.resolve() not in target.parents and target != root.resolve():
            raise RuntimeError(f"Caminho inseguro no arquivo: {member.name}")
    tar.extractall(root)
shutil.rmtree(parts_dir, ignore_errors=True)
(root / "bootstrap_repo.py").unlink(missing_ok=True)
(root / ".github/workflows/bootstrap.yml").unlink(missing_ok=True)
print("Projeto MAPD Niskier expandido com sucesso.")
