$(document).ready(function () {
    if ($.cookie('mytoken') == undefined) {
        document.getElementById("button_signin").style.display = 'inline'
        document.getElementById("button_signup").style.display = 'inline'
    } else {
        valid_check()
    }
});

// 쿠키에 가지고 있는 token을 헤더에 담아서 보냅니다.
function valid_check() {
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


// ['쿠키'라는 개념에 대해 알아봅시다]
// 로그인을 구현하면, 반드시 쿠키라는 개념을 사용합니다.
// 페이지에 관계없이 브라우저에 임시로 저장되는 정보입니다. 키:밸류 형태(딕셔너리 형태)로 저장됩니다.
// 쿠키가 있기 때문에, 한번 로그인하면 네이버에서 다시 로그인할 필요가 없는 것입니다.
// 브라우저를 닫으면 자동 삭제되게 하거나, 일정 시간이 지나면 삭제되게 할 수 있습니다.
function login() {
    $.ajax({
        type: "POST",
        url: "/api/login",
        data: {id: $('#userid').val(), pw: $('#userpw').val()},
        success: function (response) {
            if (response['result'] == 'success') {
                // 로그인이 정상적으로 되면, 토큰을 받아옵니다.
                // 이 토큰을 mytoken이라는 키 값으로 쿠키에 저장합니다.
                $.cookie('mytoken', response['token']);

                //alert('로그인 완료!')
                //window.location.href = '/'
                $('#button_signin').text("로그아웃")
                document.getElementById("button_signup").style.display = 'none'
                document.getElementById("welcome").style.display = 'none'
                document.getElementById("mycontent").style.display = 'flex'
                document.getElementById("myconfig").style.display = 'flex'
                closeLoginLayer()
                setTimeout(function() {valid_check();},100)

            } else {
                // 로그인이 안되면 에러메시지를 띄웁니다.
                alert(response['msg'])
            }
        }
    })
}


// 로그아웃은 내가 가지고 있는 토큰만 쿠키에서 없애면 됩니다.
function logout() {
    $.removeCookie('mytoken');
    //alert('로그아웃!')

    document.getElementById("button_signup").style.display = 'inline'
    document.getElementById("myconfig").style.display = 'none'
    document.getElementById("welcome").style.display = 'block'
    window.location.reload();
}

function signup() {
    window.location.href = '/register'
}

function loginButtonToggle(name) {
    if (name == "로그인") {
        openLoginLayer()
    } else if (name == "로그아웃") {
        logout()
    }
}

function openLoginLayer() {
    document.getElementById("loginlayer").style.display = 'flex'
    //$('#loginlayer').show()
}

function closeLoginLayer() {
    document.getElementById("loginlayer").style.display = 'none'
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