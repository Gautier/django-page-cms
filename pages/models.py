from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

class Language(models.Model):
    id = models.CharField(primary_key=True, maxlength=8)
    name = models.CharField(maxlength=20)
    
    def __str__(self):
        return self.name.capitalize()
    
    @classmethod
    def get_from_request(cls, request, current_page=None):
        if 'language' in request.GET:
            l=Language.objects.get(pk=request.GET['language'])
        elif 'language' in request.POST:
            l=Language.objects.get(pk=request.POST['language'])
        else:
            try:
                l=Language.objects.get(pk=request.LANGUAGE_CODE)
            except Language.DoesNotExist:
                languages = current_page.get_languages()
                if len(languages) > 0:
                    l=languages[0]
                else:
                    l=Language.objects.latest('id')
        return l

class PagePublishedManager(models.Manager):
    def get_query_set(self):
        return super(PagePublishedManager, self).get_query_set().filter(status=1)
    
class PageDraftsManager(models.Manager):
    def get_query_set(self):
        return super(PageDraftsManager, self).get_query_set().filter(status=0)

class Page(models.Model):
    """A simple hierarchical page model"""

    STATUSES = (
        (0, _('Draft')),
        (1, _('Published'))
    )
    
    # slugs are the same for each language
    slug = models.SlugField(unique=True)
    author = models.ForeignKey(User)
    parent = models.ForeignKey('self', related_name="children", blank=True, null=True)
    creation_date = models.DateTimeField(editable=False, auto_now_add=True)
    publication_date = models.DateTimeField(editable=False, null=True)
    
    status = models.IntegerField(choices=STATUSES, radio_admin=True, default=0)
    template = models.CharField(maxlength=100, null=True, blank=True)
    # TODO : add the possibility to change the order of the page acording this variable
    # order = models.IntegerField()

    # Managers
    objects = models.Manager()
    published = PagePublishedManager()
    drafts = PageDraftsManager()

    class Admin:
        pass

    def save(self):
        self.slug = slugify(self.slug)
        if self.status == 1 and self.publication_date is None:
            self.publication_date = datetime.now()
        super(Page, self).save()
        
    def title(self, lang):
        c = Content.get_content(self, lang, 0, True)
        return c
    
    def body(self, lang):
        c = Content.get_content(self, lang, 1, True)
        return c
    
    def get_absolute_url(self):
        return '/pages/'+self.get_url()
    
    def get_languages(self):
        """Get the list of all existing languages for this page"""
        contents = Content.objects.filter(page=self, type=1)
        languages = []
        for c in contents:
            languages.append(c.language.id)
        return languages
        
    def get_url(self):
        url = self.slug + '/'
        p = self.parent
        while p:
            url = p.slug + '/' + url
            p = p.parent

        return url
        
    def get_template(self):
        p = self
        while p:
            if p.template:
                return p.template
            if p.parent:
                p = p.parent
            else:
                return None

    def __str__(self):
        if self.parent:
            return "%s :: %s" % (self.parent.slug, self.slug)
        else:
            return "%s" % (self.slug)
        
class Content(models.Model):
    """A block of content, tied to a page, for a particular language"""
    CONTENT_TYPE = ((0, 'title'),(1,'body'))
    language = models.ForeignKey(Language)
    body = models.TextField()
    type = models.IntegerField(choices=CONTENT_TYPE, radio_admin=True, default=0)
    page = models.ForeignKey(Page)
    
    class Admin:
        pass
    
    def __str__(self):
        return "%s :: %s" % (self.page.title(), self.body[0:15])
    
    @classmethod
    def set_or_create_content(cls, page, language, type, body):
        try:
            c = Content.objects.get(page=page, language=language, type=type)
            c.body = body
        except Content.DoesNotExist:
            c = Content(page=page, language=language, body=body, type=type)
        c.save()
        return c
        
    @classmethod
    def get_content(cls, page, language, type, language_fallback=False):
        try:
            c = Content.objects.get(language=language, page=page, type=type)
            return c.body
        except Content.DoesNotExist:
            if language_fallback:
                try:
                    c = Content.objects.filter(page=page, type=type)
                    if len(c):
                        return c[0].body
                except Content.DoesNotExist:
                    pass
        return None

