// $("#loginBtn").click(function () {
//     let email = $("#email").val()
//     let password = $("#password").val()
//     let userData = {
//         "email": email,
//         "password": password
//     }
//     $.ajax({
//         type: "POST",
//         url: "http://127.0.0.1:5000/login",
//         dataType: "json",
//         crossDomain: true,
//         headers: {
//             "accept": "application/json",
//             "Access-Control-Allow-Origin": "*"
//         },
//         data: userData,
//         success: function (response) {
//             console.log(response)
//             if (response.status == 200) {
//                 location.href = "/"
//             } else {
//                 location.href = "/login"
//             }
//         },
//         error: function (response) {
//             console.log("Error occured")
//             console.log(response)
//         }
//     })
// })