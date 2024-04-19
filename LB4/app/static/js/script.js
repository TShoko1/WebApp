"use strict";
window.onload = function () {
    const btnDeleteUser = document.querySelectorAll(".btn-delete-user");
    if (btnDeleteUser) {
        btnDeleteUser.forEach(btn => {
            btn.addEventListener("click", (event) => {
                const deleteUserModalLabel = document.querySelector("#deleteUserModalLabel");
                const btnElement = event.target;
                if (deleteUserModalLabel) {
                    const classList = btnElement.classList.toString().split(" ");
                    const userClass = classList[classList.length - 1];
                    deleteUserModalLabel.textContent = `Вы уверены, что хотите удалить пользователя ${userClass.split("-").join(" ")}?`;
                    const btnDeleteUserConfirm = document.querySelector(".btn-delete-user-confirm");
                    const UID = classList[classList.length - 2].split("-")[1];
                    btnDeleteUserConfirm.href = `/deleteUser/${UID}`;
                }
            });
        });
    }
};
