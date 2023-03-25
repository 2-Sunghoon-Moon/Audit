import os
import subprocess

repo_list = [
    "https://github.com/koor00t/DEX_solidity",
    "https://github.com/jw-dream/DEX_solidity",
    "https://github.com/Namryeong-Kim/DEX_Solidity",
    "https://github.com/Gamj4tang/DEX_solidity",
    "https://github.com/kimziwu/DEX_solidity",
    "https://github.com/hangi-dreamer/Dex_solidity",
    "https://github.com/2-Sunghoon-Moon/DEX_solidity",
    "https://github.com/jun4n/DEX_solidity",
    "https://github.com/Sophie00Seo/DEX_solidity",
    "https://github.com/seonghwi-lee/Lending-DEX_solidity",
    "https://github.com/dlanaraa/DEX_solidity",
    "https://github.com/hyeon777/DEX_Solidity",
    "https://github.com/siwon-huh/DEX_solidity",
    "https://github.com/jt-dream/Dex_solidity",
]


for i in repo_list:
    name = i.split('/')[3]
    print(name)

    subprocess.run(["git", "submodule", "add", i + ".git", name])