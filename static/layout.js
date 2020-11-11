$(document).ready(function () {
    if ($.cookie('mytoken') == undefined) {
        document.getElementById("button_signin").style.display = 'inline';
        document.getElementById("button_signup").style.display = 'inline';
    } else {
        valid_check();
    };
});

function valid_check() {
    $.ajax({
        type: "GET",
        url: "/api/valid",
        headers: {'token': $.cookie('mytoken')},
        data: {},
        success: function (response) {
            if (response['result'] == 'success') {
                $('#button_signin').text("로그아웃");
                document.getElementById("button_signin").style.display = 'inline';
                document.getElementById("button_signup").style.display = 'none';
                document.getElementById("welcome").style.display = 'none';
                document.getElementById("myconfig").style.display = 'flex';
                document.getElementById("mycontent").style.display = 'flex';
            } else {
                alert(response['msg']);
            };
        }
    });
}

function loginButtonToggle(name) {
    if (name == "로그인") {
        openLoginLayer();
    } else if (name == "로그아웃") {
        logout();
    }
}

function openLoginLayer() {
    document.getElementById("loginlayer").style.display = 'flex';
}

function closeLoginLayer() {
    document.getElementById("loginlayer").style.display = 'none';
}

function login() {
    $.ajax({
        type: "POST",
        url: "/api/login",
        data: {id: $('#userid').val(), pw: $('#userpw').val()},
        success: function (response) {
            if (response['result'] == 'success') {
                $.cookie('mytoken', response['token']);
                setTimeout(function() {logined();},100);
                closeLoginLayer();
            } else {
                alert(response['msg']);
            };
        }
    });
}

function logined() {
    valid_check();
    $('#myport_box').empty();
    myconfigGet();
    myportRefresh();
}

function logout() {
    $.removeCookie('mytoken');
    window.location.reload();
}

function signup() {
    window.location.href = '/register'
}