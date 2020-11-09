$(document).ready(function () {
    $('#myport_box_modify').empty();
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
                let ports = response['ports_data']
                for (let i = 0; i < ports.length; i++){
                    let {code, name} = ports[i];
                    let temphtml =`<tr>
                                       <td>${i+1}</td>
                                       <td>${code}</td>
                                       <td>${name}</td>
                                       <td><a href="#" onclick="deletePort('${code}','${name}')" class="card-footer-item has-text-danger">
                                           삭제<span class="icon"><i class="fas fa-ban"></i></span>
                                       </a></td>
                                   </tr>`;
                    $('#myport_box_modify').append(temphtml);
                }
            } else if(response['result'] == 'success_but') {
                let msg = response['msg'];
                let temphtml = `<tr>
                                    <td colspan="4">${msg}</td>
                                </tr>`;
                $('#myport_box_modify').append(temphtml);
            } else {
                let msg = response['msg'];
                alert(msg);
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
    window.location.href = '/';
}