document.addEventListener("DOMContentLoaded", () => {
    document
        .querySelectorAll(".withdraw-application-form")
        .forEach((form) => {
            form.addEventListener("submit", (event) => {
                const jobTitle = form.dataset.jobTitle || "this job";
                const confirmed = window.confirm(
                    `Withdraw your application for ${jobTitle}? ` +
                    "This action cannot be undone."
                );

                if (!confirmed) {
                    event.preventDefault();
                }
            });
        });
});
