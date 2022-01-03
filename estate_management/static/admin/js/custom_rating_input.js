window.addEventListener('DOMContentLoaded', (event) => {
  const starsIndexLimit = 4;
  let lastOver = -1;
  let isHovering = false;
  let selectedRate = 0;



function loadDefaultStars(status_class="fa-star-o", rateInput){
   if (rateInput){
     const starsParent = document.createElement("div");
     const fragment = document.createDocumentFragment();
     for (let i=0; i<5; i++){
       const newStar = document.createElement("span");
       newStar.classList.add("fa",status_class,"rate_star");
       newStar.setAttribute("data-star", i);
       newStar.setAttribute("data-checked", false);
       newStar.addEventListener("click", starHandler);
       newStar.addEventListener("mouseover", overHandler);
       newStar.style.fontSize = "1.4em";
       newStar.style.color = "#1aafe8";
       fragment.appendChild(newStar);
     }
     starsParent.addEventListener("mouseleave", backDefault);
     starsParent.appendChild(fragment);
     rateInput.parentElement.insertBefore(starsParent, rateInput);
   }
}


function starHandler(event){
  const mirorInput = document.querySelector("#rate");
  const selectedStarIndex = event.target.getAttribute("data-star");
  selectedRate = selectedStarIndex;
  lastOver = selectedStarIndex;
  mirorInput.value = Number(selectedRate)+1;
}

function addTargetClassAndRemove(elm, targetClass, removed, checked){
    if (elm.classList.contains(removed)){
      elm.classList.remove(removed);
    }
    if (!elm.classList.contains(targetClass)){
      elm.classList.add(targetClass);
    }
    elm.setAttribute("data-checked", checked);
}

function highlightOrDisableStarList(starList, targetClass, removed, checked){
  starList.forEach( (star)=>{
    addTargetClassAndRemove(star, targetClass, removed, checked);
  });
}


function handleOverAddAndDudction(index){
  const starList = Array.from(document.querySelectorAll(".rate_star"));
  index = Number(index);
  if (index == starsIndexLimit){
    highlightOrDisableStarList(starList, "fa-star", "fa-star-o", true);
  } else if (index < starsIndexLimit && index == 0){
    highlightOrDisableStarList(starList.slice(1, starList.length), "fa-star-o", "fa-star", false);

  } else if (index > 0 && index < starsIndexLimit){

    highlightOrDisableStarList(starList.slice(0, index+1), "fa-star", "fa-star-o", true);
    highlightOrDisableStarList(starList.slice(index+1, starList.length), "fa-star-o", "fa-star", false);
  } else {
        highlightOrDisableStarList(starList, "fa-star-o", "fa-star", false);
  }
}

function backDefault(){
   handleOverAddAndDudction(lastOver);
}


function overHandler(event){
  const starIndex = event.target.getAttribute("data-star");
  handleOverAddAndDudction(starIndex);
}


  let rateInputCheck = document.querySelector("#rate");
  if (rateInputCheck){
    rateInputCheck.style.position = 'absolute';
    rateInputCheck.style.top = '-9999px';
    rateInputCheck.style.left = '-9999px';
    loadDefaultStars(status_class="fa-star-o", rateInputCheck);

    if (rateInputCheck.value != 0){
      let currentIndex = Number(rateInputCheck.value.trim()) - 1;
      handleOverAddAndDudction(currentIndex);
      selectedRate = currentIndex - 1;
      lastOver = currentIndex;
    }
  }
});
