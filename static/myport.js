$(document).ready(function () {
    // index.html 로드가 완료되면 자동으로 showStar() 함수를 호출합니다.
    $('#port-box').empty();
    showPort();
});

function deletePort(code) {
    $.ajax({
        type: 'POST',
        url: '/api/delete-port',
        data: {'code': code},
        success: function (response) {
            if (response['result'] == 'success') {
                let msg = response['msg'];
                // alert(msg);
            }
        }
    });
    window.location.reload();
}

function showPort() {
    $.ajax({
        type: 'GET',
        url: '/api/myport',
        headers: {'token': $.cookie('mytoken')},
        data: {},
        success: function (response) {
            if (response['result'] == 'success') {

                console.log(response)
                //     let ports = response['port']
                //     for (let i = 0; i < ports.length; i++){
                //         let {port} = ports[i]
                //         let temphtml =`<tr>
                //                            <td>${port}</td>
                //                        </tr>`
                //         $('#port-box').append(temphtml);
                //     }
            } else {
                let msg = response['msg']
                let temphtml = `<tr>
                                    <td colspan="3" style="text-align: center">${msg}</td>
                                </tr>`
                $('#port-box').append(temphtml);
            }
        }
    });
}