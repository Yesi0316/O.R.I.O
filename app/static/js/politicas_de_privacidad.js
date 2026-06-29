const modalPoliticas = document.getElementById("modal-politicas");
const checkPoliticas = document.getElementById("acepto-politicas");
const btnPoliticas = document.getElementById("btn-politicas");

const campos = formRegistro.querySelectorAll(
    "input, button, textarea, select"
);

campos.forEach(campo => {
    if (
        campo.id !== "acepto-politicas" &&
        campo.id !== "btn-politicas"
    ){
        campo.disabled = true;
    }
});

checkPoliticas.addEventListener("change", () => {
    btnPoliticas.classList.toggle(
        "activo",
        checkPoliticas.checked
    );
});

btnPoliticas.addEventListener("click", () => {

    if(!checkPoliticas.checked){
        return;
    }

    modalPoliticas.style.display = "none";

    campos.forEach(campo => {
        campo.disabled = false;
    });
});