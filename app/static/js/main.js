// window.addEventListener("load", function(){
// 	alert('loaded');
// });

$(document).ready(function(){
	$('.carousel').carousel({
		interval: false,
	})
	$("#progress_yt").css("display", "none");
	$("#progress_sc").css("display", "none");

	$.validator.addMethod(
		"ytLinkCheck",
		function(value, element) {
			return value.startsWith("https://www.youtube.com/watch?v") || value.startsWith("https://youtu.be/");
		},
		"URL should lead to the video on youtube.com."
	);

	$.validator.addMethod(
		"scLinkCheck",
		function(value, element) {
			return value.startsWith("https://soundcloud.com/");
		},
		"URL should lead to the file on soundcloud.com."
	);

	$.validator.addMethod(
		"ytCorrectnessCheck",
		function(value, element) {
			if (value.startsWith("https://www.youtube.com/watch?v")){
				if (value.length < 43){
					return false;
				}else{
					return true;
				}
			}
			if (value.startsWith("https://youtu.be/")){
				if (value.length < 28){
					return false;
				}else{
					return true;
				}
			}
		},
		"Please check link for correctness."
	);

	$.validator.addMethod(
		"scCorrectnessCheck",
		function(value, element) {
			var splittedStr = value.slice(8, ).split("/");
			if (splittedStr.length == 3 && splittedStr[2] != "sets"){
				return true;
			}else if(splittedStr.length == 4 && splittedStr[2] == "sets"){
				return true;
			}
			else{
				return false;
			}
		},
		"Please check link for correctness."
	);

	$.validator.addMethod(
		"usernameCheck",
		function(value, element) {
			return !value.includes("@");
		}
	);

	$.validator.addMethod(
		"itemsCheck",
		function(value, element) {
			var num1 = $("#first_item_number").val();
			num1 = parseInt(num1);
			num1 = Number.isInteger(num1)

			var num2 = $("#last_item_number").val();
			num2 = parseInt(num2);
			num2 = Number.isInteger(num2)
			return num1 && num2;
		},
		"Please enter both items numbers."
	);

	$.validator.addMethod(
		"item1Check",
		function(value, element) {
			var num1 = $("#first_item_number").val();
			num1 = parseInt(num1);
			if (num1 >= 1){
				return true;
			}
			return false;
		},
		"Bad first item number."
	);

	$.validator.addMethod(
		"item2Check",
		function(value, element) {
			var num1 = $("#first_item_number").val();
			num1 = parseInt(num1);

			var num2 = $("#last_item_number").val();
			num2 = parseInt(num2);

			return num1 < num2;
		},
		"Bad last item number."
	);

	$("#dfyt").validate({
		errorLabelContainer: "#ytErrorLabelContainer",
		errorClass: "error",
	  rules: {
			link: {
				required: true,
				url: true,
				ytLinkCheck: true,
				ytCorrectnessCheck: true
			}
		},
		messages: {
			link: {
				required: "Please enter URL."
			}
		},
		submitHandler: function(form) {
			$("#BtnSubmit1").prop("disabled", true);
			$("#carousel-control1").prop("disabled", true);
			$("#carousel-control2").prop("disabled", true);
			$("#progress_yt").css("display", "block");
			$("#progress_yt").html("Checking url");

			var interval;
			interval = setInterval(function() {
        $.ajax('/get_progress').done(
          function(response) {
						console.log(response);
						if (response["Status_code"] == 0){
							$("#progress_yt").html(response["Progress"]);
						}
						else{
							console.log("Stopping status checker");
							$("#progress_yt").css("display", "none");
							$("#BtnSubmit1").prop("disabled", false);
							$("#carousel-control1").prop("disabled", false);
							$("#carousel-control2").prop("disabled", false);
							clearInterval(interval);
						}
          }
				);
      }, 2000);
			return true
		}
	});

	$("#dfsc").validate({
		errorLabelContainer: "#scErrorLabelContainer",
		errorClass: "error",
	  rules: {
			link: {
				required: true,
				url: true,
				scLinkCheck: true,
				scCorrectnessCheck: true
			}
		},
		messages: {
			link: {
				required: "Please enter URL."
			}
		},
		submitHandler: function(form) {
			$("#BtnSubmit2").prop("disabled", true);
			$("#carousel-control1").prop("disabled", true);
			$("#carousel-control2").prop("disabled", true);
			$("#progress_sc").css("display", "block");
			$("#progress_sc").html("Downloading");

			var interval;
			interval = setInterval(function() {
        $.ajax('/get_progress').done(
          function(response) {
						console.log(response);
						if (response["Status_code"] == 0){
							$("#progress_sc").html(response["Progress"]);
						}
						else{
							console.log("Stopping status checker");
							$("#progress_sc").css("display", "none");
							$("#BtnSubmit2").prop("disabled", false);
							$("#carousel-control1").prop("disabled", false);
							$("#carousel-control2").prop("disabled", false);
							clearInterval(interval);
						}
          }
				);
      }, 2000);
			return true
		}
	});

	$("#signUpForm").validate({
		errorClass: "error",
	  rules: {
			username: {
				required: true,
				minlength: 4,
				usernameCheck: true,
				maxlength: 32
			},
			email: {
				required: true,
				email: true
			},
			password: {
				minlength : 8,
				required: true
			},
			repeat_password: {
				equalTo : "#password"
			}
		},
		messages: {
			username: {
				required: "<-- This field is required.",
				minlength: "<-- Username must be at least 4 symbols long.",
				usernameCheck: "<-- Username should not contain \"@\", please use a different username.",
				maxlength: "<-- Username must be less than 32 symbols."
			},
			email: {
				email: "<-- Enter a valid email address.",
				required: "<-- This field is required."
			},
			password: {
				required: "<-- This field is required.",
				minlength: "<-- Password must be at least 8 symbols long."
			},
			repeat_password: {
				required: "<-- This field is required.",
				equalTo: "<-- This field should match password."
			}
		}
	});

	$("#signInForm").validate({
		errorClass: "error",
	  rules: {
			username: {
				required: true,
				minlength: 4,
				usernameCheck: true,
				maxlength: 32
			},
			password: {
				minlength : 8,
				required: true
			}
		},
		messages: {
			username: {
				required: "<-- This field is required.",
				minlength: "<-- Username must be at least 4 symbols long.",
				usernameCheck: "<-- Username should not contain \"@\", please use a different username.",
				maxlength: "<-- Username must be less than 32 symbols."
			},
			password: {
				required: "<-- This field is required.",
				minlength: "<-- Password must be at least 8 symbols long."
			}
		}
	});

	$("#changePasswordForm").validate({
		errorClass: "error",
		rules: {
			password: {
				minlength : 8,
				required: true
			},
			repeat_password: {
				equalTo : "#password"
			}
		},
		messages: {
			password: {
				required: "<-- This field is required.",
				minlength: "<-- Password must be at least 8 symbols long."
			},
			repeat_password: {
				required: "<-- This field is required.",
				equalTo: "<-- This field should match password."
			}
		}
	});

	$("#requestPasswordChangeForm").validate({
		errorClass: "error",
		rules: {
			email: {
				required: true,
				email: true
			}
		},
		messages: {
			email: {
				email: "<-- Enter a valid email address.",
				required: "<-- This field is required."
			}
		}
	});

	$("#DownloadPlaylistForm").validate({
		errorClass: "error",
		rules: {
			link: {
				required: true,
				url: true,
				itemsCheck: true,
				item1Check: true,
				item2Check: true
			},
			first_item_number: {
				required: false
			},
			last_item_number: {
				required: false
			}
		},
		messages: {
			link: {
				required: "Please enter URL."
			}
		}
	});
});
