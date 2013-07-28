function applyPostJS() {
	$('.editPostLink').click(function(event) {
		event.preventDefault();

		var me = $(this);
		if (me.data('alreadyEditing') == true) return false;
		me.data('alreadyEditing', true);

		var postID = me.data('postId');
		me.prop('disabled', true);

		showLoadOverlay();

		$.ajax({
			url: me.attr('href') + '?getQuickEditAjaxForm=yes',
			type: 'GET',
			error: function(jqXHR, textStatus, errorThrown) {
				// TODO: SHOW ERROR
				hideLoadOverlay();
				me.prop('disabled', false);
			},
			success: function(data, textStatus, jqXHR) {
				hideLoadOverlay();
				//var postContentWrapper = $('#postContentWrapper'+postID);
				var postContent = $('#postContent'+postID);
				var postSignature = $('#postSignature'+postID);

				postContent.hide();
				postSignature.hide();
				postContent.after(data.form_html);
				var qeWidget = $('#quickEditPost'+postID);
				var qeForm = $('#quickEditForm'+postID);
				var result = $('#quickEditResult'+postID);

				$('#cancelEdit'+postID).click(function(event) {
					event.preventDefault();
					qeForm.remove();
					postContent.show();
					postSignature.show();
					me.removeData('alreadyEditing');
					me.prop('disabled', false);
				});

				qeForm.submit(function(event) {
					event.preventDefault();

					var submitButton = $('#quickEditForm'+postID+' :submit');
					submitButton.prop('disabled', true);
					result.text('');

					showLoadOverlay();

					$.ajax({
						url: me.attr('href') + '?ajax=yes',
						type: 'POST',
						data: qeForm.serialize(),
						error: function(jqXHR, textStatus, errorThrown) {
							hideLoadOverlay();

							result.text('Something went wrong (' + textStatus + '). Please try again.');
							submitButton.prop('disabled', false);
						},
						success: function(data, textStatus, jqXHR) {
							hideLoadOverlay();

							if (data.was_edited) {
								postContent.html(data.post_html);
								qeForm.remove();
								postContent.show();
								postSignature.show();
								me.removeData('alreadyEditing');
								me.prop('disabled', false);

								toast('Your post has been saved.');
							} else {
								result.text('There were errors');
								submitButton.prop('disabled', false);
							}
						}
					});
				});
			}
		});

	});

	$('.deletePostLink').click(function(event) {
		event.preventDefault();

		var me = $(this);
		var postID = me.data('postId');

		var confirmButton = $('#confirmOverlayButton');

		activateConfirmOverlay(
			'Are you sure you want to delete this post?',
			'Delete Post',
			function() {
				confirmButton.prop('disabled', true);
				showLoadOverlay();

				$.ajax({
					url: me.attr('href') + '?ajax=yes',
					type: 'POST',
					data: {'_csrf_token': csrfToken},
					error: function(jqXHR, textStatus, errorThrown) {
						hideLoadOverlay();
						confirmButton.prop('disabled', false);
						toast('Something went wrong (' + textStatus + '). Try again?');
					},
					success: function(data, textStatus, jqXHR) {
						hideLoadOverlay();
						deactivateOverlay();
						toast('This post has been deleted.');
					}
				});
			});
	});
}

$(document).ready(function() {
	$('#quickReply').submit(function(event) {
		event.preventDefault();

		if ($('#quickReply input[name="content"]').val() == '') {
			$('#quickReplyResult').fadeIn(200).text('You must enter a post.');
			return;
		}

		$('#quickReply :submit').prop('disabled', true);
		$('#quickReplyResult').fadeOut(200);

		showLoadOverlay();

		$.ajax({
			url: replyURL + '?ajax=yes',
			type: 'POST',
			data: $(this).serialize(),
			error: function(jqXHR, textStatus, errorThrown) {
				hideLoadOverlay();

				var msg = 'Something went wrong while submitting the post (status code ' + jqXHR.status + '). Please try again shortly.';

				$('#quickReplyResult').fadeIn(200).text(msg);
				//console.log(errorThrown);
				$('#quickReply :submit').prop('disabled', false);
			},
			success: function(data, textStatus, jqXHR) {
				hideLoadOverlay();

				if (data.was_posted) {
					if (data.layout_extra.style_url)
						addExtraCSS(data.layout_extra.style_url);

					$('#postsContainer').append(data.post_html);
					var newPost = $('#post'+data.post_id);
					// from http://blog.pengoworks.com/index.cfm/2009/4/21/Fixing-jQuerys-slideDown-effect-ie-Jumpy-Animation
					//var height = newPost.height();
					//newPost.css({height:0});
					//newPost.animate({height: height}, {duration: 500});
					newPost.hide();
					newPost.fadeIn(500);
					$('#quickReply :submit').prop('disabled', false);
					$('#quickReply textarea[name="content"]').val('');
					applyPostJS();

					toast('Your reply has been posted.');
				} else {
					$('#quickReplyResult').text('Something went wrong while submitting the post.');
					$('#quickReply :submit').prop('disabled', false);
				}
			}
		});
	});

	$('.modActionLink').click(function(event) {
		event.preventDefault();
		var me = $(this);
		var clsName = me.data('clsName');
		me.prop('disabled', true);

		showLoadOverlay();
		$.ajax({
			url: me.attr('href'),
			type: 'POST',
			data: {'_csrf_token': csrfToken, 'ajax': true},
			error: function(jqXHR, textStatus, errorThrown) {
				hideLoadOverlay();
				toast('An error occurred (' + jqXHR.status + '). Please try again shortly.');
				me.prop('disabled', false);
			},
			success: function(data, textStatus, jqXHR) {
				hideLoadOverlay();
				toast(data.toast);
				me.prop('disabled', false);
				$('.'+clsName).text(data.link_title);
			}
		});
	});

	applyPostJS();
});
