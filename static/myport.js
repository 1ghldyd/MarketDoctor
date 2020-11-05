$(document).ready(function () {
    // index.html 로드가 완료되면 자동으로 showStar() 함수를 호출합니다.
    $('#port-box').empty();
    showPort();
});

function showPort() {
    $.ajax({
        type: 'GET',
        url: '/api/myport',
        headers: {'token': $.cookie('mytoken')},
        data: {},
        success: function (response) {
            if (response['result'] == 'success') {
                let ports = response['ports_info']
                console.log(response)
                for (let i = 0; i < ports.length; i++){
                    let {code, name} = ports[i]
                    let temphtml =`<tr>
                                       <td>${i+1}</td>
                                       <td>${code}</td>
                                       <td>${name}</td>
                                       <td><a href="#" onclick="deletePort('${code}','${name}')" class="card-footer-item has-text-danger">
                                           삭제<span class="icon"><i class="fas fa-ban"></i></span>
                                       </a></td>
                                   </tr>`
                    $('#port-box').append(temphtml);
                }
            } else {
                let msg = response['msg']
                let temphtml = `<tr>
                                    <td colspan="4">${msg}</td>
                                </tr>`
                $('#port-box').append(temphtml);
            }
        }
    });
}

function addPort(code) {
    $.ajax({
        type: 'POST',
        url: '/api/addport',
        headers: {'token': $.cookie('mytoken')},
        data: {'code': code},
        success: function (response) {
            if (response['result'] == 'success') {
                let msg = response['msg'];
                alert(msg);
                window.location.reload();
            }
        }
    });
}


function deletePort(code,name) {
    $.ajax({
        type: 'POST',
        url: '/api/deleteport',
        headers: {'token': $.cookie('mytoken')},
        data: {'code': code,'name':name},
        success: function (response) {
            if (response['result'] == 'success') {
                let msg = response['msg'];
                alert(msg);
                window.location.reload();
            }
        }
    });

}

function backtothehome() {
    window.location.href = '/'
}