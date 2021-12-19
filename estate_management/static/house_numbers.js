window.addEventListener('DOMContentLoaded', (event) => {
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
    const checkIfForm = document.querySelector("form");
    if (checkIfForm){
      const houseSelect = document.querySelector("#housenumber");
      let apiUrl = `/get_houses_numbers?street=${streetSelect.value}`;
      if (userName && userName.value != ""){
        apiUrl = `/get_houses_numbers?street=${streetSelect.value}&username=${userName.value}`;
      }
      const res = await fetch(apiUrl);
      const data = await res.json();
      console.log(data);
      if (data.code == 200){
        data.houses.forEach( (houseOption, index)=>{
          let newHouse = document.createElement("option");
          newHouse.setAttribute("value", houseOption);
          newHouse.innerText = houseOption;
          // if this edit form so select the user room
          houseSelect.appendChild(newHouse);
        });
      }


    }
  }

  onFlaskFormLoad();

  const streetSelectInput = document.querySelector("#streetname");
  async function myFunction(){
    const houseSelect = document.querySelector("#housenumber");
    const res = await fetch(`/get_houses_numbers?street=${streetSelectInput.value}`);
    const data = await res.json();
    console.log(data);
    if (data.code == 200){
      houseSelect.innerHTML = "";
      data.houses.forEach( (houseOption, index)=>{
        let newHouse = document.createElement("option");
        newHouse.setAttribute("value", houseOption);
        newHouse.innerText = houseOption;
        houseSelect.appendChild(newHouse);
      });
    }
  }

  if (streetSelectInput){
    streetSelectInput.addEventListener("change", myFunction);
  }

});
