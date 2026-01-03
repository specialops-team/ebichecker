document.addEventListener("DOMContentLoaded", () => {
  console.log("Script Loaded Correctly"); // Check your browser console for this!

  const form = document.getElementById("checkerForm");
  const fileInput = document.getElementById("catalog_file");
  const submitBtn = document.getElementById("submitBtn");
  const statusDiv = document.getElementById("statusMessage");
  const modal = document.getElementById("validationModal");
  const tableBody = document.getElementById("validationTableBody");
  const downloadBtn = document.getElementById("downloadErrorsBtn");
  const closeIconBtn = document.getElementById("closeIconBtn");

  let currentErrors = [];
  let currentFilename = "Catalog";

  // --- Modal Functions ---
  const openModal = () => {
    modal.classList.remove("hidden");
    document.body.style.overflow = "hidden"; // Prevent background scrolling
  };

  const closeModal = () => {
    modal.classList.add("hidden");
    document.body.style.overflow = ""; // Restore scrolling
  };

  closeIconBtn.addEventListener("click", closeModal);

  // Close modal when clicking outside the white box
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  // --- Render Errors to Table ---
  function showErrors(errors) {
    tableBody.innerHTML = "";

    errors.forEach((err) => {
      const tr = document.createElement("tr");
      tr.className =
        "border-b border-gray-100 last:border-0 hover:bg-gray-50 transition";

      tr.innerHTML = `
                <td class="py-3 px-2 align-top text-center">
                    <svg class="w-6 h-6 text-red-500 inline-block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                    </svg>
                </td>
                <td class="py-3 px-2 text-gray-700 font-medium text-sm leading-6">
                    <div class="flex flex-col">
                        <span>
                            <span class="font-bold text-gray-900 bg-gray-200 px-1 rounded text-xs mr-2">${err.ID}</span>
                            <span class="font-semibold text-blue-700">${err.Title}</span>
                        </span>
                        <span class="mt-1 text-red-600">${err.Issue}</span>
                    </div>
                </td>
            `;
      tableBody.appendChild(tr);
    });
    openModal();
  }

  // --- Form Submission ---
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // 1. Reset UI
    statusDiv.classList.add("hidden");
    statusDiv.className = "hidden mt-6 p-4 rounded-md text-center font-medium"; // Reset classes
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Processing...`;

    // 2. Capture Filename
    if (fileInput.files.length > 0) {
      currentFilename = fileInput.files[0].name;
    }

    try {
      const formData = new FormData(form);

      // 3. Send Request
      const response = await fetch("/check_catalog", {
        method: "POST",
        body: formData,
      });

      // 4. Handle Response
      const result = await response.json();

      statusDiv.classList.remove("hidden");

      if (!response.ok) {
        throw new Error(result.error || "Unknown Server Error");
      }

      if (result.status === "issues_found") {
        // FAILURE CASE (Issues found)
        currentErrors = result.errors;
        showErrors(result.errors);

        statusDiv.classList.add(
          "bg-red-50",
          "text-red-700",
          "border",
          "border-red-200"
        );
        statusDiv.innerHTML = `<strong>Attention:</strong> Found ${result.errors.length} issues in your catalog.`;
      } else {
        // SUCCESS CASE
        statusDiv.classList.add(
          "bg-green-50",
          "text-green-700",
          "border",
          "border-green-200"
        );
        statusDiv.innerHTML = `<svg class="w-6 h-6 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg> ${result.message}`;
      }
    } catch (error) {
      // ERROR CASE
      console.error(error);
      statusDiv.classList.remove("hidden");
      statusDiv.classList.add(
        "bg-red-100",
        "text-red-800",
        "border",
        "border-red-300"
      );
      statusDiv.textContent = `System Error: ${error.message}`;
    } finally {
      // 5. Restore Button
      submitBtn.disabled = false;
      submitBtn.textContent = "Run Checker";
    }
  });

  // --- Download Button ---
  downloadBtn.addEventListener("click", async () => {
    const originalText = downloadBtn.textContent;
    downloadBtn.textContent = "Generating...";
    downloadBtn.disabled = true;

    try {
      const response = await fetch("/download_errors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          errors: currentErrors,
          filename: currentFilename,
        }),
      });

      if (!response.ok) throw new Error("Download failed");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Errors_${currentFilename.replace(/\.[^/.]+$/, "")}.xlsx`; // Smart renaming
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (error) {
      alert("Failed to download file: " + error.message);
    } finally {
      downloadBtn.textContent = originalText;
      downloadBtn.disabled = false;
    }
  });
});
