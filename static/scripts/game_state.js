//check if cookie exists with name token and if it does, set the token to the value of the cookie
if (document.cookie.indexOf("token") !== -1) {
  token = document.cookie;
  token = token.replace("token=", "");
  console.log(token);

  //save the html content of the page /token/status to the variable status
  var status = $.get("/" + token + "/status", function (data) {
    status = data;
    console.log("status = " + status);
  });
}
