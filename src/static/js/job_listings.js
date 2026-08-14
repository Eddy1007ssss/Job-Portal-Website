document.addEventListener("DOMContentLoaded", function () {
    const sortForm = document.getElementById("sortForm");
    const sortSelect = document.getElementById("sort");

    if (sortForm && sortSelect) {
        sortSelect.addEventListener("change", function () {
            sortForm.submit();
        });
    }

    document.querySelectorAll("[data-company-logo]").forEach(function (image) {
        const showFallback = function () {
            image.hidden = true;

            const logoContainer = image.closest(".job-logo");

            if (logoContainer) {
                logoContainer.classList.remove("has-logo");
            }
        };

        image.addEventListener("error", showFallback);

        if (image.complete && image.naturalWidth === 0) {
            showFallback();
        }
    });

    const flashMessages = document.querySelectorAll(".flash-message");

    if (flashMessages.length > 0) {
        window.setTimeout(function () {
            flashMessages.forEach(function (message) {
                message.classList.add("hide");
            });
        }, 4500);
    }
});
