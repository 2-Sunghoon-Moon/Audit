import os
import subprocess

repo_list = [
    "https://github.com/koor00t/Lending_solidity",
    "https://github.com/jw-dream/Leding-DEX-solidity",
    "https://github.com/Namryeong-Kim/Lending_solidity",
    "https://github.com/Gamj4tang/Lending_solidity",
    "https://github.com/kimziwu/Lending_solidity",
    "https://github.com/hangi-dreamer/Lending_solidity",
    "https://github.com/2-Sunghoon-Moon/Lending_solidity",
    "https://github.com/jun4n/Lending_solidity",
    "https://github.com/Sophie00Seo/Lending_solidity",
    "https://github.com/seonghwi-lee/Lending",
    "https://github.com/dlanaraa/Lending_solidity",
    "https://github.com/hyeon777/Lending_Solidity",
    "https://github.com/siwon-huh/Lending_solidity",
]


for i in repo_list:
    name = i.split('/')[3]
    print(name)

    subprocess.run(["git", "submodule", "add", i + ".git", name])