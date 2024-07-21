{{ name | escape | underline}}

.. currentmodule:: {{ module }}

.. auto{{ objtype }}:: {{ fullname }}

{% block members %}
{% if members %}
.. rubric:: {{ _('Members') }}

.. autosummary::
   :nosignatures:
   :template: only_names_in_toc.rst
{% for item in members %}
   {% if not item.startswith('_') %}
   ~{{ name }}.{{ item }}
   {% endif %}
{%- endfor %}
{% endif %}
{% endblock %}
