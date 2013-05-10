var activeOverlay = null;
var showingLoadOverlay = false;
var overlayIsTemporary = false;

var confirmCallback = null;

function activateOverlay(id, callback) {
	var elem = $('#'+id);
	activeOverlay = elem;
	overlayIsTemporary = false;

	$('#overlayWrapper').fadeIn(400, callback);
	elem.show();
}

function activateDynamicOverlay(html) {
	var wrapper = $('#overlayWrapper');
	var elem = $.parseHTML(html);
	elem.appendTo(wrapper);

	activeOverlay = elem;
	overlayIsTemporary = true;

	wrapper.fadeIn(400);
	elem.show();
}

function activateConfirmOverlay(message, buttonTitle, callback) {
	$('#confirmOverlayMessage').text(message);
	$('#confirmOverlayButton').prop('disabled', false).text(buttonTitle);
	confirmCallback = callback;
	activateOverlay('confirmOverlay');
}

function deactivateOverlay() {
	$('#overlayWrapper').fadeOut(400, function() {
		if (overlayIsTemporary)
			activeOverlay.remove();
		else
			activeOverlay.hide();
		activeOverlay = null;
		confirmCallback = null;
	});
}

function showLoadOverlay() {
	if (showingLoadOverlay) return;
	showingLoadOverlay = true;
	$('#workingOverlay').fadeIn(200);
}

function hideLoadOverlay() {
	if (!showingLoadOverlay) return;
	showingLoadOverlay = false;
	$('#workingOverlay').fadeOut(200);
}


function toast(message) {
	var elem = $(document.createElement('div'));
	elem.addClass('flashToast');
	elem.text(message);
	$('#workingOverlay').after(elem);

	elem.hide();
	elem.fadeIn(400);
	setTimeout(function() {
		elem.fadeOut(400, elem.remove);
	}, 3000);
}



$(document).ready(function() {
	$('#loginLink').click(function(event) {
		event.preventDefault();

		activateOverlay('loginFormOverlay', function() {
			$('#login_name').focus();
		});
	});

	$('#overlayBG').click(function(event) {
		deactivateOverlay();
	});

	$('#confirmOverlayButton').click(function(event) {
		if (confirmCallback != null)
			confirmCallback();
	});
});