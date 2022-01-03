function addJsCodes(){
  const wtf_phone_field = document.getElementById('telephone');
  if (wtf_phone_field){
    wtf_phone_field.style.position = 'absolute';
    wtf_phone_field.style.top = '-9999px';
    wtf_phone_field.style.left = '-9999px';
    wtf_phone_field.required = false;
    wtf_phone_field.parentElement.insertAdjacentHTML('beforeend', '<div><input class="form-control" type="tel" id="_phone"></div>');
    const fancy_phone_field = document.getElementById('_phone');
    const fancy_phone_iti = window.intlTelInput(fancy_phone_field, {
        separateDialCode: true,
        utilsScript: "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/16.0.4/js/utils.js",
    });
    fancy_phone_iti.setNumber(wtf_phone_field.value);
    fancy_phone_field.addEventListener('blur', function() {
        wtf_phone_field.value = fancy_phone_iti.getNumber();
    });
    fancy_phone_field.required = true;
    return true;
  } else {
    return false;
  }
}

$( document ).ready(function() {
  const isFormHere = document.querySelector("form.admin-form");
  if (isFormHere){addJsCodes();}

});
