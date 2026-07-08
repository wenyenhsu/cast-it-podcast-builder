-- Align the UI/UX slug with Django's slugify("UI/UX") == "uiux", which is
-- what the backend and publisher generate.
update public.tags set slug = 'uiux' where slug = 'ui-ux';
