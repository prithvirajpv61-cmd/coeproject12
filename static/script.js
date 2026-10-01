// SmartBiz — compare-selection behaviour on the results page.
document.addEventListener("DOMContentLoaded", function () {
  var checkboxes = document.querySelectorAll(".compare-checkbox");
  var bar = document.getElementById("compareBar");
  var countLabel = document.getElementById("compareCount");
  var goLink = document.getElementById("compareGo");

  if (!checkboxes.length || !bar) return;

  var MAX_COMPARE = 3;

  function update() {
    var checked = Array.prototype.filter.call(checkboxes, function (cb) {
      return cb.checked;
    });

    checkboxes.forEach(function (cb) {
      cb.disabled = !cb.checked && checked.length >= MAX_COMPARE;
    });

    if (checked.length === 0) {
      bar.style.display = "none";
      return;
    }
    bar.style.display = "flex";
    countLabel.textContent = checked.length + " scheme" + (checked.length > 1 ? "s" : "") + " selected (max 3)";

    var ids = checked.map(function (cb) { return cb.value; }).join(",");
    goLink.href = "/compare?ids=" + ids;
    goLink.style.pointerEvents = checked.length >= 2 ? "auto" : "none";
    goLink.style.opacity = checked.length >= 2 ? "1" : "0.5";
    goLink.textContent = checked.length >= 2
      ? "Compare selected →"
      : "Select at least 2 to compare";
  }

  checkboxes.forEach(function (cb) {
    cb.addEventListener("change", update);
  });

  update();
});

// Password visibility toggle
document.addEventListener("click", function (e) {
  var btn = e.target.closest(".password-toggle-btn");
  if (!btn) return;

  var targetId = btn.getAttribute("data-toggle-target");
  var input = document.getElementById(targetId);
  if (!input) return;

  var isPassword = input.type === "password";
  input.type = isPassword ? "text" : "password";
  btn.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");

  var eyeOpen = btn.querySelector(".eye-open");
  var eyeClosed = btn.querySelector(".eye-closed");
  if (eyeOpen && eyeClosed) {
    eyeOpen.style.display = isPassword ? "none" : "block";
    eyeClosed.style.display = isPassword ? "block" : "none";
  }
});

// Mobile navigation menu toggle
document.addEventListener("DOMContentLoaded", function () {
  var menuBtn = document.getElementById("mobileMenuBtn");
  var mobileNav = document.getElementById("mobileNav");

  if (menuBtn && mobileNav) {
    menuBtn.addEventListener("click", function () {
      var isExpanded = menuBtn.getAttribute("aria-expanded") === "true";
      menuBtn.setAttribute("aria-expanded", !isExpanded);
      mobileNav.classList.toggle("is-open");

      var iconMenu = menuBtn.querySelector(".icon-menu");
      var iconClose = menuBtn.querySelector(".icon-close");
      if (iconMenu && iconClose) {
        iconMenu.style.display = isExpanded ? "block" : "none";
        iconClose.style.display = isExpanded ? "none" : "block";
      }
    });
  }
});

// Toast notification helper
function showToast(message, type) {
  var stack = document.querySelector(".flash-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.className = "flash-stack";
    var main = document.querySelector("main.page");
    if (main) main.insertBefore(stack, main.firstChild);
  }
  if (!stack) return;

  var toast = document.createElement("div");
  toast.className = "flash flash-" + (type || "success");
  toast.innerHTML = '<span>' + message + '</span>';
  stack.appendChild(toast);

  setTimeout(function () {
    toast.style.transition = "opacity 0.3s ease, transform 0.3s ease";
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-6px)";
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 350);
  }, 4000);
}

// Universal Save / Unsave Scheme handler (Toggle Button)
document.addEventListener("click", function (e) {
  var btn = e.target.closest(".btn-save-toggle");
  if (!btn) return;

  var schemeId = btn.getAttribute("data-scheme-id");
  if (!schemeId) return;

  if (btn.disabled) return;

  var isCurrentlySaved = btn.classList.contains("is-saved");
  var url = isCurrentlySaved ? "/api/unsave-scheme" : "/api/save-scheme";

  var textSpan = btn.querySelector(".save-btn-text");
  var originalText = textSpan ? textSpan.textContent : (isCurrentlySaved ? "Saved" : "Save");
  var isDetailsPage = originalText.toLowerCase().indexOf("scheme") !== -1;

  // Immediate loading state
  btn.disabled = true;
  if (textSpan) {
    textSpan.textContent = isCurrentlySaved ? "Removing..." : "Saving...";
  }

  fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "X-Requested-With": "XMLHttpRequest"
    },
    body: JSON.stringify({ scheme_id: parseInt(schemeId, 10) })
  })
  .then(function (res) {
    if (!res.ok) throw new Error("HTTP error " + res.status);
    return res.json();
  })
  .then(function (data) {
    btn.disabled = false;
    if (data && data.success) {
      if (data.saved) {
        btn.classList.add("is-saved");
        btn.setAttribute("aria-label", "Remove from saved");
        btn.innerHTML = '<svg class="save-icon" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path></svg><span class="save-btn-text">' + (isDetailsPage ? "Saved Scheme" : "Saved") + '</span>';
        showToast("Scheme saved to your profile.", "success");
      } else {
        btn.classList.remove("is-saved");
        btn.setAttribute("aria-label", "Save scheme");
        btn.innerHTML = '<svg class="save-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path></svg><span class="save-btn-text">' + (isDetailsPage ? "Save Scheme" : "Save") + '</span>';
        showToast("Scheme removed from saved.", "success");
      }
    } else {
      throw new Error(data && data.error ? data.error : "Failed to update save state");
    }
  })
  .catch(function (err) {
    console.error("Save scheme error:", err);
    btn.disabled = false;
    if (textSpan) textSpan.textContent = originalText;
    showToast("Unable to save this scheme. Please try again.", "error");
  });
});

// Remove button handler on Saved Schemes page
document.addEventListener("click", function (e) {
  var btn = e.target.closest(".btn-unsave");
  if (!btn) return;

  var schemeId = btn.getAttribute("data-scheme-id");
  var cardId = btn.getAttribute("data-card-id");
  if (!schemeId) return;

  if (btn.disabled) return;

  var textSpan = btn.querySelector(".unsave-btn-text");
  var originalText = textSpan ? textSpan.textContent : "Remove";

  btn.disabled = true;
  if (textSpan) textSpan.textContent = "Removing...";

  fetch("/api/unsave-scheme", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "X-Requested-With": "XMLHttpRequest"
    },
    body: JSON.stringify({ scheme_id: parseInt(schemeId, 10) })
  })
  .then(function (res) {
    if (!res.ok) throw new Error("HTTP error " + res.status);
    return res.json();
  })
  .then(function (data) {
    if (data && data.success) {
      var card = cardId ? document.getElementById(cardId) : null;
      if (card) {
        card.style.transition = "opacity 0.3s ease, transform 0.3s ease";
        card.style.opacity = "0";
        card.style.transform = "scale(0.96)";
        setTimeout(function () {
          if (card.parentNode) card.parentNode.removeChild(card);
          var remaining = document.querySelectorAll(".saved-scheme-item");
          if (remaining.length === 0) {
            var grid = document.getElementById("savedGrid");
            var empty = document.getElementById("savedEmptyState");
            if (grid) grid.style.display = "none";
            if (empty) empty.style.display = "block";
          }
        }, 320);
      }
      showToast("Removed from saved schemes.", "success");
    } else {
      throw new Error(data && data.error ? data.error : "Failed to remove scheme");
    }
  })
  .catch(function (err) {
    console.error("Unsave error:", err);
    btn.disabled = false;
    if (textSpan) textSpan.textContent = originalText;
    showToast("Unable to remove scheme. Please try again.", "error");
  });
});

// Client-side Form Validation
document.addEventListener("DOMContentLoaded", function () {
  // 1. Password confirmation validation for Register form
  var registerForm = document.querySelector('form[action*="register"]');
  if (registerForm) {
    registerForm.addEventListener("submit", function (e) {
      var pass = registerForm.querySelector('input[name="password"]');
      var confirm = registerForm.querySelector('input[name="confirm_password"]');
      if (pass && confirm && pass.value !== confirm.value) {
        e.preventDefault();
        showToast("Passwords do not match. Please verify.", "error");
        confirm.focus();
      }
    });
  }

  // 2. Password confirmation validation for Reset Password form
  var resetForm = document.querySelector('form[action*="reset-password"]');
  if (resetForm) {
    resetForm.addEventListener("submit", function (e) {
      var pass = resetForm.querySelector('input[name="new_password"]');
      var confirm = resetForm.querySelector('input[name="confirm_password"]');
      if (pass && confirm && pass.value !== confirm.value) {
        e.preventDefault();
        showToast("Passwords do not match. Please verify.", "error");
        confirm.focus();
      }
    });
  }

  // 3. Find schemes form numeric validation
  var findForm = document.querySelector('form[action*="results"]');
  if (findForm) {
    findForm.addEventListener("submit", function (e) {
      var loan = findForm.querySelector('input[name="loan_amount"]');
      var turnover = findForm.querySelector('input[name="annual_turnover"]');
      if (loan && parseFloat(loan.value) <= 0) {
        e.preventDefault();
        showToast("Please enter a valid positive loan amount.", "warning");
        loan.focus();
      } else if (turnover && parseFloat(turnover.value) < 0) {
        e.preventDefault();
        showToast("Turnover cannot be negative.", "warning");
        turnover.focus();
      }
    });
  }
});
