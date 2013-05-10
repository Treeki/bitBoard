function updateSelectedPostStyle() {
	var elem = $('#post_style-0');
	var html = $('html');

	html.removeClass('epSimplePostStyle epAdvancedPostStyle');
	if (elem.prop('checked'))
		html.addClass('epSimplePostStyle');
	else
		html.addClass('epAdvancedPostStyle');
}

$(document).ready(function() {
	updateSelectedPostStyle();
	
	$('#post_style-0, #post_style-1').change(function(event) {
		updateSelectedPostStyle();
	});
});