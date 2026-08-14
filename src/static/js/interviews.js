document.addEventListener("DOMContentLoaded", function () {
    const interviewMode = document.getElementById("interviewMode");
    const locationInput = document.getElementById("locationOrLink");
    const locationLabel = document.getElementById("locationOrLinkLabel");
    const locationHelp = document.getElementById("locationOrLinkHelp");

    const fieldSettings = {
        Online: {
            label: "Meeting Link",
            placeholder: "https://meet.example.com/interview",
            help: "Enter a complete http or https meeting link.",
        },
        "In-person": {
            label: "Interview Location",
            placeholder: "Office name, building and full address",
            help: "Enter the location where the applicant should attend.",
        },
        Phone: {
            label: "Phone Number / Call Instructions",
            placeholder: "+60 12-345 6789 or employer will call applicant",
            help: "Explain how the phone interview will begin.",
        },
    };

    function updateLocationField() {
        if (!interviewMode || !locationInput || !locationLabel || !locationHelp) {
            return;
        }

        const settings = fieldSettings[interviewMode.value];

        if (!settings) {
            return;
        }

        locationLabel.textContent = settings.label;
        locationInput.placeholder = settings.placeholder;
        locationHelp.textContent = settings.help;
    }

    if (interviewMode) {
        interviewMode.addEventListener("change", updateLocationField);
        updateLocationField();
    }

    function closeReasonDialog(dialog) {
        if (typeof dialog.close === "function") {
            dialog.close();
        } else {
            dialog.removeAttribute("open");
        }
    }

    document.querySelectorAll("[data-open-dialog]").forEach(function (button) {
        button.addEventListener("click", function () {
            const dialogId = button.getAttribute("data-open-dialog");
            const dialog = document.getElementById(dialogId);

            if (!dialog) {
                return;
            }

            if (typeof dialog.showModal === "function") {
                dialog.showModal();
            } else {
                dialog.setAttribute("open", "");
            }

            const reasonField = dialog.querySelector("textarea[name='reason']");

            if (reasonField) {
                reasonField.focus();
            }
        });
    });

    document.querySelectorAll("[data-close-dialog]").forEach(function (button) {
        button.addEventListener("click", function () {
            const dialog = button.closest("dialog");

            if (dialog) {
                closeReasonDialog(dialog);
            }
        });
    });

    document.querySelectorAll(".interview-reason-dialog").forEach(function (dialog) {
        dialog.addEventListener("click", function (event) {
            if (event.target === dialog) {
                closeReasonDialog(dialog);
            }
        });
    });
});
