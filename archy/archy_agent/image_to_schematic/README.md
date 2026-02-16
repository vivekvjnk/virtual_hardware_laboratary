# Special steps
1. Dependency with bpe_simple_vocab_16e6 model
    - As of now, in SAMv3 the model path is hardcoded. Hence the module expects the model in hardcoded directory
## Temporary fix
- Create the assets directory in python site packages
```bash
mkdir -p /home/pst/Documents/virtual_hardware_laboratory/.venv/lib/python3.13/site-packages/assets
```
- Make sure path is correct 
- Download the model
```bash
curl -L https://github.com/openai/CLIP/raw/main/clip/bpe_simple_vocab_16e6.txt.gz \
  -o /home/pst/Documents/virtual_hardware_laboratory/.venv/lib/python3.13/site-packages/assets/bpe_simple_vocab_16e6.txt.gz
```
