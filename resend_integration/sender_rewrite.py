import email.utils
import inspect

SENDING_DOMAIN = "noreply.kartoza.com"
SENDING_EMAIL = f"noreply@{SENDING_DOMAIN}"


def patch_queue_builder():
	"""Rewrite every outgoing email's sender to the Resend-verified domain.

	Resend rejects any `From` address whose domain isn't verified on the
	Resend account. Only `noreply.kartoza.com` is verified there, while
	most senders in this system are on the unverified `kartoza.com`. This
	patch swaps the From address to `noreply@noreply.kartoza.com` while
	keeping the original sender's display name and setting Reply-To to
	their real address, so the email still looks and behaves like it came
	from them.
	"""
	# Imported lazily: this module is imported from resend_integration's
	# package __init__, which loads before frappe's own submodules are
	# safe to import at module scope.
	from frappe.email.doctype.email_queue.email_queue import QueueBuilder

	original_init = QueueBuilder.__init__
	init_signature = inspect.signature(original_init)

	def patched_init(self, *args, **kwargs):
		bound = init_signature.bind_partial(self, *args, **kwargs)
		bound.apply_defaults()

		sender = bound.arguments.get("sender")
		if sender and sender != "Administrator":
			display_name, address = email.utils.parseaddr(sender)
			if address and address.rsplit("@", 1)[-1].lower() != SENDING_DOMAIN:
				if not bound.arguments.get("reply_to"):
					bound.arguments["reply_to"] = address
				bound.arguments["sender"] = email.utils.formataddr(
					(display_name or address, SENDING_EMAIL)
				)

		original_init(*bound.args, **bound.kwargs)

	QueueBuilder.__init__ = patched_init
