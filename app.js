const characterForm = document.getElementById("character-form");
const characterList = document.getElementById("character-list");
const rollButton = document.getElementById("roll-dice");
const diceResult = document.getElementById("dice-result");
const soundStatus = document.getElementById("sound-status");
const stopSoundButton = document.getElementById("stop-sound");
const gallery = document.getElementById("gallery");
const soundButtons = document.querySelectorAll(".sound-button");

const characters = [];
let audioContext;
let activeNodes = [];

const galleryImages = [
  {
    title: "Moonlit Keep",
    src: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='500'><defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='%231a244a'/><stop offset='1' stop-color='%23050a1a'/></linearGradient></defs><rect width='100%' height='100%' fill='url(%23g)'/><circle cx='650' cy='95' r='55' fill='%23e0e8ff'/><rect x='220' y='150' width='220' height='250' fill='%235e6078'/><polygon points='190,150 330,50 470,150' fill='%23777b95'/><rect x='285' y='220' width='35' height='180' fill='%2323283f'/><rect x='342' y='220' width='35' height='180' fill='%2323283f'/><rect x='0' y='400' width='800' height='100' fill='%230d141f'/></svg>",
  },
  {
    title: "Ancient Forest",
    src: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='500'><rect width='100%' height='100%' fill='%230f2c1c'/><rect y='340' width='100%' height='160' fill='%23133720'/><g fill='%233d7a42'><circle cx='120' cy='210' r='90'/><circle cx='320' cy='180' r='110'/><circle cx='520' cy='205' r='95'/><circle cx='700' cy='190' r='100'/></g><g fill='%2328462d'><rect x='95' y='210' width='30' height='230'/><rect x='300' y='180' width='35' height='260'/><rect x='505' y='200' width='32' height='240'/><rect x='685' y='190' width='36' height='250'/></g><path d='M0 350 C150 290, 250 410, 410 350 S700 300, 800 360' stroke='%23d6c37a' stroke-width='9' fill='none'/></svg>",
  },
  {
    title: "Dragon's Lair",
    src: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='500'><rect width='100%' height='100%' fill='%2321120f'/><ellipse cx='420' cy='420' rx='340' ry='110' fill='%23452d1f'/><g fill='%23d88d1d'><circle cx='300' cy='300' r='30'/><circle cx='380' cy='275' r='40'/><circle cx='460' cy='305' r='34'/><circle cx='535' cy='280' r='37'/><circle cx='610' cy='315' r='28'/></g><path d='M130 340 Q260 180 470 230 Q620 260 690 330' stroke='%2385401d' stroke-width='30' fill='none' stroke-linecap='round'/><circle cx='545' cy='260' r='16' fill='%23f44336'/><circle cx='543' cy='258' r='6' fill='%23fff'/></svg>",
  },
];

function renderCharacters() {
  characterList.innerHTML = "";
  characters.forEach((character) => {
    const card = document.createElement("article");
    card.className = "character-card";

    const title = document.createElement("h3");
    title.textContent = `${character.name} (Lv ${character.level} ${character.className})`;

    const stats = document.createElement("p");
    stats.textContent = `Ancestry: ${character.ancestry || "—"} • HP: ${character.hp} • AC: ${character.ac}`;

    const notes = document.createElement("p");
    notes.textContent = character.notes || "No notes";

    card.append(title, stats, notes);
    characterList.append(card);
  });
}

characterForm.addEventListener("submit", (event) => {
  event.preventDefault();

  characters.unshift({
    name: document.getElementById("character-name").value.trim(),
    className: document.getElementById("character-class").value.trim(),
    level: Number(document.getElementById("character-level").value),
    ancestry: document.getElementById("character-ancestry").value.trim(),
    hp: Number(document.getElementById("character-hp").value),
    ac: Number(document.getElementById("character-ac").value),
    notes: document.getElementById("character-notes").value.trim(),
  });

  renderCharacters();
  characterForm.reset();
  document.getElementById("character-level").value = "1";
  document.getElementById("character-hp").value = "0";
  document.getElementById("character-ac").value = "10";
});

rollButton.addEventListener("click", () => {
  const sides = Number(document.getElementById("dice-type").value);
  const count = Math.max(1, Number(document.getElementById("dice-count").value) || 1);
  const modifier = Number(document.getElementById("dice-modifier").value) || 0;
  const rolls = Array.from({ length: count }, () => Math.floor(Math.random() * sides) + 1);
  const total = rolls.reduce((sum, value) => sum + value, 0) + modifier;
  const modifierLabel = modifier >= 0 ? `+${modifier}` : `${modifier}`;
  diceResult.textContent = `${count}d${sides}: [${rolls.join(", ")}] ${modifierLabel} = ${total}`;
});

function stopAmbient() {
  activeNodes.forEach((node) => {
    try {
      node.stop?.();
    } catch {
      // no-op
    }
    try {
      node.disconnect?.();
    } catch {
      // no-op
    }
  });
  activeNodes = [];
  soundStatus.textContent = "No ambient sound playing.";
}

function playAmbient(soundName) {
  if (!audioContext) {
    audioContext = new AudioContext();
  }

  stopAmbient();

  const gain = audioContext.createGain();
  gain.gain.value = 0.04;
  gain.connect(audioContext.destination);

  const oscillator = audioContext.createOscillator();
  const filter = audioContext.createBiquadFilter();
  filter.type = "lowpass";

  if (soundName === "tavern") {
    oscillator.type = "triangle";
    oscillator.frequency.value = 180;
    filter.frequency.value = 420;
  } else if (soundName === "forest") {
    oscillator.type = "sine";
    oscillator.frequency.value = 130;
    filter.frequency.value = 260;
  } else {
    oscillator.type = "sawtooth";
    oscillator.frequency.value = 70;
    filter.frequency.value = 160;
  }

  oscillator.connect(filter);
  filter.connect(gain);
  oscillator.start();

  activeNodes = [oscillator, filter, gain];
  soundStatus.textContent = `${soundName[0].toUpperCase() + soundName.slice(1)} ambience playing.`;
}

soundButtons.forEach((button) => {
  button.addEventListener("click", () => playAmbient(button.dataset.sound));
});

stopSoundButton.addEventListener("click", stopAmbient);

galleryImages.forEach((item) => {
  const card = document.createElement("figure");
  card.className = "gallery-item";

  const img = document.createElement("img");
  img.src = item.src;
  img.alt = item.title;

  const caption = document.createElement("p");
  caption.textContent = item.title;

  card.append(img, caption);
  gallery.append(card);
});
