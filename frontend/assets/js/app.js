document.addEventListener('DOMContentLoaded', () => {

  // ─────────────────────────────────────────
  // 1. MENU DROPDOWN
  // ─────────────────────────────────────────
  document.querySelectorAll('.menu-trigger').forEach(trigger => {
    trigger.addEventListener('click', () => {
      const container = trigger.parentElement;
      const isOpen = container.classList.contains('open');
      document.querySelectorAll('.menu-container').forEach(c => c.classList.remove('open'));
      if (!isOpen) container.classList.add('open');
    });
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.menu-container')) {
      document.querySelectorAll('.menu-container').forEach(c => c.classList.remove('open'));
    }
  });

  // ─────────────────────────────────────────
  // 2. IMAGE SLIDER
  // ─────────────────────────────────────────
  const wrapper = document.getElementById("sliderWrapper");
  const slides = wrapper.querySelectorAll(".sliderItem");

  const prevBtn = document.getElementById("imgslideBtnL");
  const nextBtn = document.getElementById("imgslideBtnR");

  let index = 1;
  const slideWidth = 100;
  const intervalTime = 3000;
  let autoSlide;

  const firstClone = slides[0].cloneNode(true);
  const lastClone = slides[slides.length - 1].cloneNode(true);

  firstClone.id = "first-clone";
  lastClone.id = "last-clone";

  wrapper.appendChild(firstClone);
  wrapper.insertBefore(lastClone, slides[0]);

  const allSlides = wrapper.querySelectorAll(".sliderItem");

  wrapper.style.transform = `translateX(-${slideWidth * index}%)`;

  function moveSlider() {
    wrapper.style.transition = "transform 0.6s ease";
    wrapper.style.transform = `translateX(-${slideWidth * index}%)`;
  }

  nextBtn.addEventListener("click", () => {
    if (index >= allSlides.length - 1) return;
    index++;
    moveSlider();
  });

  prevBtn.addEventListener("click", () => {
    if (index <= 0) return;
    index--;
    moveSlider();
  });

  wrapper.addEventListener("transitionend", () => {

    if (allSlides[index].id === "first-clone") {
      wrapper.style.transition = "none";
      index = 1;
      wrapper.style.transform = `translateX(-${slideWidth * index}%)`;
    }

    if (allSlides[index].id === "last-clone") {
      wrapper.style.transition = "none";
      index = allSlides.length - 2;
      wrapper.style.transform = `translateX(-${slideWidth * index}%)`;
    }

  });

  function startAutoSlide() {
    autoSlide = setInterval(() => {
      index++;
      moveSlider();
    }, intervalTime);
  }

  const slider = document.querySelector(".slider");

  slider.addEventListener("mouseenter", () => {
    clearInterval(autoSlide);
  });

  slider.addEventListener("mouseleave", () => {
    startAutoSlide();
  });

  startAutoSlide();

  // ─────────────────────────────────────────
  // 3. PRODUCT CARD SLIDER
  // ─────────────────────────────────────────

  const cardWrapper = document.getElementById("sliderTrack");
  const cards = cardWrapper.querySelectorAll(".deal-card");

  const cardPrevBtn = document.getElementById("homeItemsPrevBtn");
  const cardNextBtn = document.getElementById("homeItemsNextBtn");

  let cardIndex = 0;

  const cardWidth = cards[0].offsetWidth + 16;
  const cardsVisible = 4;
  const maxIndex = cards.length - cardsVisible;

  function moveCardSlider() {
    cardWrapper.style.transition = "transform 0.4s ease";
    cardWrapper.style.transform = `translateX(-${cardIndex * cardWidth}px)`;

    cardPrevBtn.disabled = cardIndex === 0;
    cardNextBtn.disabled = cardIndex >= maxIndex;
  }

  cardNextBtn.addEventListener("click", () => {
    if (cardIndex < maxIndex) {
      cardIndex++;
      moveCardSlider();
    }
  });

  cardPrevBtn.addEventListener("click", () => {
    if (cardIndex > 0) {
      cardIndex--;
      moveCardSlider();
    }
  });

  moveCardSlider();

});

// ─────────────────────────────────────────
// 3. USER LOGIN
// ─────────────────────────────────────────

const API = "http://127.0.0.1:8000/auth"

async function userLogin() {

  let email = document.getElementById("email").value
  let password = document.getElementById("password").value

  let response = await fetch(API + "/login", {

    method: "POST",

    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    },

    body: `email=${email}&password=${password}`

  })

  let data = await response.json()

  if (data.token) {

    localStorage.setItem("token", data.token)

    document.getElementById("message").innerText = "Login successful"

  } else {

    document.getElementById("message").innerText = "Login failed"

  }
}

// ─────────────────────────────────────────
// 3. ADMIN LOGIN
// ─────────────────────────────────────────

async function adminLogin() {

  let email = document.getElementById("admin_email").value
  let password = document.getElementById("admin_password").value

  let response = await fetch(API + "/login", {

    method: "POST",

    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    },

    body: `email=${email}&password=${password}`

  })

  let data = await response.json()

  if (data.token) {

    let payload = JSON.parse(atob(data.token.split('.')[1]))

    if (payload.role === "admin") {

      localStorage.setItem("token", data.token)

      document.getElementById("admin_message").innerText = "Admin login successful"

    } else {

      document.getElementById("admin_message").innerText = "Not an admin account"

    }

  } else {

    document.getElementById("admin_message").innerText = "Login failed"

  }

}