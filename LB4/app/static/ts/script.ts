window.onload = function () {
    const btnDeleteUser = document.querySelectorAll(".btn-delete-user") as NodeListOf<HTMLButtonElement>;
    if (btnDeleteUser) {
        btnDeleteUser.forEach(btn => {
            btn.addEventListener("click", (event: MouseEvent) => {
                const deleteUserModalLabel = document.querySelector("#deleteUserModalLabel") as HTMLLabelElement;
                const btnElement = event.target as Element;

                if (deleteUserModalLabel) {
                    const classList = btnElement.classList.toString().split(" ");
                    const userClass = classList[classList.length - 1];
                    deleteUserModalLabel.textContent = `Вы уверены, что хотите удалить пользователя ${userClass.split("-").join(" ")}?`;

                    const btnDeleteUserConfirm = document.querySelector(".btn-delete-user-confirm") as HTMLAnchorElement;
                    const UID = classList[classList.length - 2].split("-")[1];
                    btnDeleteUserConfirm.href = `/deleteUser/${UID}`
                }
            });
        });
    }
}
