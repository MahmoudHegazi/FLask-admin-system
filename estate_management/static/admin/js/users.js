
$( document ).ready(function() {
  /* this to fix crtical problem at flask-admin add custom way to detect if id input changed
  by abuser inspect its rare case but I like 0 errors specialy when I know the error*/
  const streetnameInput = document.querySelector("#streetname");
  const theSaveButton = document.querySelector("input[type='submit']");

  let current_options = [];
  if (streetnameInput && theSaveButton){
    const streetOptions = Array.from(streetnameInput.options);
    streetOptions.forEach( (op)=>{
      current_options.push(op.value);
    });
    if (streetOptions.length > 0){
      theSaveButton.addEventListener("click", customStreetValdation);
    }
  }
  function customStreetValdation(event){
    if (streetnameInput && !current_options.includes(streetnameInput.value)){
      alert("Invalid streetname value");
      event.preventDefault();
    }
  }

  /*
    This Function when run when a form included it will create JS select input with the
    default loaded streetname and add house number on that select this select will used
    to guide creator of the house number or to select the house number
  */
  async function onFlaskFormLoad(){
    // this for edit form check if username onload that means edit form
    // add this to the request
    const userName = document.querySelector("#username");

    const streetSelect = document.querySelector("#streetname");
    const checkIfForm = document.querySelector("form.admin-form");
    if (checkIfForm){
      let checkSelect = document.querySelector("#realSelect");
      if (!checkSelect){
        const mySelectBox = document.createElement("select");
        const houseString = document.querySelector("#housenumber");
        const houseStringCont = houseString.parentElement;
        mySelectBox.classList.add("form-control")
        mySelectBox.id = "realSelect";
        houseStringCont.appendChild(mySelectBox);
        mySelectBox.addEventListener("change", customFlaskAdminUnpredefinedSelect);
        houseString.setAttribute("readonly", "readonly");
        let apiUrl = `/get_houses_numbers?street=${streetSelect.value}`;
        if (userName && userName.value != ""){
          apiUrl = `/get_houses_numbers?street=${streetSelect.value}&username=${userName.value}`;
        }
        const res = await fetch(apiUrl);
        const data = await res.json();
        console.log(data);
        if (data.code == 200 && mySelectBox){
          data.houses.forEach( (houseOption, index)=>{
            let newHouse = document.createElement("option");
            newHouse.setAttribute("value", houseOption);
            newHouse.innerText = houseOption;
            // if this edit form so select the user room
            if (data.selected != 0 && data.selected == houseOption){
              houseString.value = houseOption;
              newHouse.setAttribute("selected", "true");
            } else {
              if (index == 0){houseString.value = houseOption;}
            }

            mySelectBox.appendChild(newHouse);
          });
        }


      }
    }
  }

  onFlaskFormLoad();

});






/*    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/16.0.4/css/intlTelInput.css">

  this function will called to change the string input value to my custom js select
  value and then use that string to house number which required by flask-admin
*/
function customFlaskAdminUnpredefinedSelect(){
  const theSelect = document.querySelector("#realSelect");
  const houseString = document.querySelector("#housenumber");
  houseString.value = theSelect.value;
  return true;
}
/* This function added by Python and Jinja it must exist before any load or anything
   flask admin hook that will listen on street input change and then it will send
   get request to secured endpoint with role superadmin required and get the housenumbers
   using the streetname selected and then create options and add to my select input
*/
async function myFunction(){
  const streetSelect = document.querySelector("#streetname");
  const houseString = document.querySelector("#housenumber");
  const houseStringCont = houseString.parentElement;

  const theSelect = document.querySelector("#realSelect");
  const res = await fetch(`/get_houses_numbers?street=${streetSelect.value}`);
  const data = await res.json();
  console.log(data);
  if (data.code == 200 && theSelect){
    theSelect.innerHTML = "";
    data.houses.forEach( (houseOption, index)=>{
      if (index == 0){
        houseString.value = houseOption;
      }
      let newHouse = document.createElement("option");
      newHouse.setAttribute("value", houseOption);
      newHouse.innerText = houseOption;
      theSelect.appendChild(newHouse);
    });
  }
}
