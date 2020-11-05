

function valid_check1() {
    $.ajax({
        type: "GET",
        url: "/api/nick",
        headers: {'token': $.cookie('mytoken')},
        data: {},
        success: function (response) {
            if (response['result'] == 'success') {
                console.log(response)
                // 올바른 결과값을 받으면 nickname을 입력해줍니다.
                $('#user_id').text(response['id'])
                $('#button_signin').text("로그아웃")
                document.getElementById("button_signin").style.display = 'inline'
                document.getElementById("button_signup").style.display = 'none'
                document.getElementById("welcome").style.display = 'none'
                document.getElementById("mycontent").style.display = 'flex'
                document.getElementById("myconfig").style.display = 'flex'


            } else {
                // 에러가 나면 메시지를 띄우고 로그인 창으로 이동합니다.
                alert(response['msg'])
                //window.location.href = '/login'

            }
        }
    })
}

function myportPost() {
    $.ajax({
        type: "POST",
        url: "/api/myport",
        headers: {'token': $.cookie('mytoken')},
        data: {},
        success: function (response) {
            if (response['result'] == 'success') {
                console.log(response)
                let ports = response['port']
                for (let i = 0; i < ports.length; i++){
                    let {port} = ports[i]
                    let temphtml =`<tr>
                                       <td>${port}</td>
                                   </tr>`
                    $('#port-box').append(temphtml);
                }


            } else {
                // 에러가 나면 메시지를 띄우고 로그인 창으로 이동합니다.
                alert(response['msg'])
                //window.location.href = '/login'

            }
        }
    })
}


function myportGet() {
    $.ajax({
        type: "GET",
        url: "/api/myport",
        headers: {'token': $.cookie('mytoken')},
        data: {},
        success: function (response) {
            if (response['result'] == 'success') {
                console.log(response)
                let ports = response['port']
                for (let i = 0; i < ports.length; i++){
                    let {port} = ports[i]
                    let temphtml =`<tr>
                                       <td>${port}</td>
                                   </tr>`
                    $('#port-box').append(temphtml);
                }
            } else {
                // 에러가 나면 메시지를 띄우고 로그인 창으로 이동합니다.
                alert(response['msg'])
                $('#loading').text("등록 된 종목이 없습니다.")
                //window.location.href = '/login'

            }
        }
    })
}

function myportPost() {
    $.ajax({
        type: "GET",
        url: "/api/myport",
        headers: {'token': $.cookie('mytoken')},
        data: {},
        success: function (response) {
            if (response['result'] == 'success') {
                console.log(response)
                let ports = response['port']
                for (let i = 0; i < ports.length; i++){
                    let {port} = ports[i]
                    let temphtml =`<tr>
                                       <td>${port}</td>
                                   </tr>`
                    $('#port-box').append(temphtml);
                }
            } else {
                // 에러가 나면 메시지를 띄우고 로그인 창으로 이동합니다.
                alert(response['msg'])
                $('#loading').text("등록 된 종목이 없습니다.")
                //window.location.href = '/login'

            }
        }
    })
}

function myport(){
    window.location.href = '/myport'
}