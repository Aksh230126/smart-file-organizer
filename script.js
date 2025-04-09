document.addEventListener("DOMContentLoaded", function() {
    const fileInput = document.getElementById("fileInput");
    const fileNameDisplay = document.getElementById("fileName");

    fileInput.addEventListener("change", function() {
        if (fileInput.files.length > 0) {
            fileNameDisplay.textContent = `Selected File: ${fileInput.files[0].name}`;
        }
    });
});
