let total = 0;

function selectProduct(price){

total = price;

document.getElementById("total").innerText =
"$ " + total.toLocaleString();

}