let homeSocket = io()
homeSocket.connect("http://127.0.0.1:5001/")

homeSocket.on('connect', function (msg) {
    homeSocket.emit('getCryptoData', {data: 'start'})
})


homeSocket.on("receiveCryptoData", function (data) {
    console.log(data)
    $("#tdata").empty()
    currencies = data.data.data
    for (let currency of currencies) {
        let element = `
                <tr>
                    <td>${currency.name}</td>
                    <td>${currency.sname}</td>
                    <td>${currency.ammount[0]}</td>
                    <td>${currency.ammount[1]}</td>
                    <td>${currency.ammount[2]}</td>
                </tr>
            `
        $("#tdata").append(element)
    }
})
