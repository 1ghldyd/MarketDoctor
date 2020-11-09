$(document).ready(function () {
    $('#myport_box').empty();
    myconfigGet();
    myportRefresh();
});

function myconfigGet() {
    $.ajax({
        type: "GET",
        url: "/api/myconfig",
        headers: {'token': $.cookie('mytoken')},
        data: {},
        success: function (response) {
            if (response['result'] == 'success') {
                $('#user_id').text(response['payload']['email'])
                if (response['payload']['notice_rate_up'] == "" && response['payload']['notice_rate_down'] == "") {
                    $('#notice_rate').text('우측 수정하기 버튼 클릭 후, 알람 조건을 설정해 주세요. 전일 대비 등락률이 설정값에 도달하면 이메일 알람이 발송됩니다.');
                    document.getElementById("notice_rate").style.fontWeight = 'bolder';
                    document.getElementById("notice_rate").style.color = 'khaki';
                } else {
                    let up
                    let down
                    if (response['payload']['notice_rate_up'] == ""){
                        up = "";
                    } else {
                        up = '[ '+ response['payload']['notice_rate_up'] + '% 이상일 때 ] ';
                    }
                    if (response['payload']['notice_rate_down'] == ""){
                        down = "";
                    } else {
                        down = '[ '+ response['payload']['notice_rate_down'] + '% 이하일 때 ]';
                    }
                    $('#notice_rate').text(up + down);
                };
            } else {
                //let msg = response['msg'];
                //alert(msg);
            };
        }
    });
}

function myconfigModify() {
    $.ajax({
        type: "GET",
        url: "/api/myconfig",
        headers: {'token': $.cookie('mytoken')},
        data: {},
        success: function (response) {
            if (response['result'] == 'success') {
                document.getElementById("useremail").placeholder = response['payload']['email'];
                if (response['payload']['notice_rate_up'] !== "") {
                    document.getElementById("notice_rate_up").placeholder = response['payload']['notice_rate_up'];
                } else {
                    document.getElementById("notice_rate_up").placeholder = '이상값을 입력';
                };
                if (response['payload']['notice_rate_up'] !== "") {
                    document.getElementById("notice_rate_down").placeholder = response['payload']['notice_rate_down'];
                } else {
                    document.getElementById("notice_rate_down").placeholder = '이하값을 입력';
                };
            } else {
                let msg = response['msg'];
                alert(msg);
            };
        }
    });
    document.getElementById("configlayer").style.display = 'flex';
}

function saveMyConfig() {
    if ($('#useremail').val() == "") {
        email = document.getElementById("useremail").placeholder;
    } else {
        email = $('#useremail').val();
    };
    if ($('#notice_rate_up').val() == "") {
        notice_rate_up = document.getElementById("notice_rate_up").placeholder;
    } else {
        notice_rate_up = $('#notice_rate_up').val();
    };
    if ($('#notice_rate_down').val() == "") {
        notice_rate_down = document.getElementById("notice_rate_down").placeholder;
    } else {
        notice_rate_down = $('#notice_rate_down').val();
    };
    $.ajax({
        type: "POST",
        url: "/api/myconfig",
        headers: {'token': $.cookie('mytoken')},
        data: {'email':email, 'notice_rate_up':notice_rate_up,'notice_rate_down':notice_rate_down},
        success: function (response) {
            if (response['result'] == 'success') {
                let msg = response['msg'];
                alert(msg);
                closeconfiglayer();
            } else {
                let msg = response['msg'];
                alert(msg);
            };
        }
    });
}

function closeconfiglayer() {
    document.getElementById("configlayer").style.display = 'none';
}


function myportRefresh() {
    $('#myport_box').empty();
    let temphtml =`<tr>
                       <th scope="col" id="loading" colspan="4">로딩중..</th>
                   </tr>`
    $('#myport_box').append(temphtml);

    $.ajax({
        type: "GET",
        url: "/api/myport-refresh",
        headers: {'token': $.cookie('mytoken')},
        data: {},
        success: function (response) {
            if (response['result'] == 'success') {
                let ports = response['ports_data']
                $('#myport_box').empty();
                for (let i = 0; i < ports.length; i++){
                    let {code, name, current_price, debi, rate, volume} = ports[i];
                    temphtml =`<tr>
                                   <td style="vertical-align: middle">${i+1}</td>
                                   <td>${name}<br/>${code}</td>
                                   <td>${current_price.toLocaleString()}<br/>${volume.toLocaleString()}</td>
                                   <td>${debi.toLocaleString()}<br/>${rate}%</td>
                               </tr>`;
                    $('#myport_box').append(temphtml);
                }
            } else if(response['result'] == 'success_but') {
                let msg = response['msg'];
                $('#myport_box').empty();
                let temphtml = `<tr>
                                    <td colspan="4">${msg}</td>
                                </tr>`;
                $('#myport_box').append(temphtml);
            } else {
                //let msg = response['msg'];
                //alert(msg);
            };
        }
    });
}

function myportModify(){
    window.location.href = '/myport-modify';
}